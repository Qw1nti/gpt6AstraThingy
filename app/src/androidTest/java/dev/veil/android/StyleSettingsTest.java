package dev.veil.android;

import android.content.*;
import android.graphics.Bitmap;
import android.os.*;
import android.view.*;
import android.widget.*;
import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.*;
import org.junit.runner.RunWith;
import java.io.*;
import static org.junit.Assert.*;

@RunWith(AndroidJUnit4.class)
public final class StyleSettingsTest {
    private Context context;
    private Prefs prefs;
    @Before public void setup(){context=InstrumentationRegistry.getInstrumentation().getTargetContext();prefs=new Prefs(context);prefs.p.edit().clear().commit();CustomMaskImage.remove(context);}
    @After public void cleanup(){prefs.p.edit().clear().commit();CustomMaskImage.remove(context);}
    private ActivityScenario<MainActivity> launch(){return ActivityScenario.launch(new Intent(context,MainActivity.class).putExtra("tab",1));}
    private View find(MainActivity a,String tag){return a.getWindow().getDecorView().findViewWithTag(tag);}
    private void click(MainActivity a,String tag){View v=find(a,tag);assertNotNull(tag,v);assertTrue(tag,v.performClick());}

    @Test public void styleControlsAreContextualAndKeepExistingValues(){
        prefs.put("color",2);prefs.put("pixelSize",37);prefs.put("borderColor",1);prefs.p.edit().putString("label","MY LABEL").commit();
        try(ActivityScenario<MainActivity> scenario=launch()){
            scenario.onActivity(a->{
                assertNull(find(a,"pixel-size"));assertNull(find(a,"custom-image-picker"));
                click(a,"style-5");assertEquals(5,prefs.style());assertNotNull(find(a,"pixel-size"));assertNull(find(a,"color-0"));assertEquals(37,prefs.pixelSize());
                click(a,"style-4");assertNotNull(find(a,"custom-image-picker"));assertNull(find(a,"pixel-size"));
                click(a,"style-3");assertNull(find(a,"censor-text"));assertNotNull(find(a,"color-0"));
                click(a,"style-2");assertEquals(View.VISIBLE,find(a,"label-options").getVisibility());assertEquals("MY LABEL",((EditText)find(a,"censor-text")).getText().toString());
                click(a,"style-0");assertEquals(2,prefs.p.getInt("color",-1));assertEquals(37,prefs.pixelSize());assertEquals(1,prefs.p.getInt("borderColor",-1));
                assertEquals(View.GONE,find(a,"label-options").getVisibility());
            });
        }
    }
    @Test public void coverageAndExpandedSectionsSurviveRecreation(){
        try(ActivityScenario<MainActivity> scenario=launch()){
            scenario.onActivity(a->{
                click(a,"coverage-reset");assertEquals(0,prefs.p.getInt("padding",99));
                click(a,"coverage-minus");assertEquals(-1,prefs.p.getInt("padding",99));
                click(a,"coverage-plus");assertEquals(0,prefs.p.getInt("padding",99));
                ((SeekBar)find(a,"coverage-slider")).setProgress(0);click(a,"coverage-minus");assertEquals(-40,prefs.p.getInt("padding",99));
                ((SeekBar)find(a,"coverage-slider")).setProgress(110);click(a,"coverage-plus");assertEquals(70,prefs.p.getInt("padding",99));
                click(a,"category-toggle");click(a,"advanced-toggle");click(a,"style-5");
            });
            scenario.recreate();
            scenario.onActivity(a->{assertNotNull(find(a,"pixel-size"));assertEquals(70,prefs.p.getInt("padding",99));assertEquals(View.VISIBLE,find(a,"category-options").getVisibility());assertEquals(View.VISIBLE,find(a,"advanced-options").getVisibility());});
        }
    }
    @Test public void previewChangesWithStyleAndCoverage(){
        try(ActivityScenario<MainActivity> scenario=launch()){
            scenario.onActivity(a->{
                StylePreviewView view=(StylePreviewView)find(a,"style-preview");view.layout(0,0,320,180);
                click(a,"coverage-reset");click(a,"style-0");click(a,"color-1");
                Bitmap output=Bitmap.createBitmap(320,180,Bitmap.Config.ARGB_8888);view.draw(new android.graphics.Canvas(output));
                int covered=output.getPixel(130,90);assertEquals(Ui.PINK,covered);
                ((SeekBar)find(a,"coverage-slider")).setProgress(0);view.draw(new android.graphics.Canvas(output));assertNotEquals(covered,output.getPixel(130,90));
                click(a,"style-3");view.draw(new android.graphics.Canvas(output));assertNotEquals(Ui.PINK,output.getPixel(163,90));output.recycle();
            });
        }
    }
    @Test public void nativeScreenshotsAndLargeTextLayout()throws Exception{
        String oldScale=shell("settings get system font_scale").trim();
        try{
            shell("wm size 1080x2400");shell("wm density 420");shell("settings put system font_scale 1.0");SystemClock.sleep(350);
            try(ActivityScenario<MainActivity> scenario=launch()){
                screenshot("01-settings-compact.png");
                scenario.onActivity(a->click(a,"style-5"));screenshot("02-pixelated-compact.png");
                scenario.onActivity(a->{ScrollView scroll=(ScrollView)find(a,"main-scroll");scroll.scrollTo(0,Ui.dp(a,480));});screenshot("03-coverage-compact.png");
            }
            shell("wm size 1768x2208");SystemClock.sleep(350);
            try(ActivityScenario<MainActivity> scenario=launch()){screenshot("04-settings-expanded.png");}
            shell("wm size 1080x2400");shell("settings put system font_scale 1.5");SystemClock.sleep(350);
            try(ActivityScenario<MainActivity> scenario=launch()){
                screenshot("05-settings-large-text.png");
                scenario.onActivity(a->{
                    for(int i=0;i<6;i++){
                        Button b=(Button)find(a,"style-"+i);assertTrue("style touch height",b.getHeight()>=Ui.dp(a,48));assertNotNull(b.getLayout());
                        assertTrue("style label fits",b.getLayout().getHeight()<=b.getHeight()-b.getCompoundPaddingTop()-b.getCompoundPaddingBottom());
                    }
                });
            }
        }finally{shell("wm size reset");shell("wm density reset");shell("settings put system font_scale "+(oldScale.equals("null")?"1.0":oldScale));}
    }
    private String shell(String command)throws IOException{
        try(ParcelFileDescriptor fd=InstrumentationRegistry.getInstrumentation().getUiAutomation().executeShellCommand(command);InputStream in=new ParcelFileDescriptor.AutoCloseInputStream(fd)){return new String(in.readAllBytes(),java.nio.charset.StandardCharsets.UTF_8);}
    }
    private void screenshot(String name)throws IOException{
        InstrumentationRegistry.getInstrumentation().waitForIdleSync();SystemClock.sleep(250);
        Bitmap image=InstrumentationRegistry.getInstrumentation().getUiAutomation().takeScreenshot();assertNotNull(image);
        File folder=new File(context.getExternalFilesDir(null),"ui-screenshots");assertTrue(folder.isDirectory()||folder.mkdirs());
        try(OutputStream out=new FileOutputStream(new File(folder,name))){assertTrue(image.compress(Bitmap.CompressFormat.PNG,100,out));}finally{image.recycle();}
    }
}
