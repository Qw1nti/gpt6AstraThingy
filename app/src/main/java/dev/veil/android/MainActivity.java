package dev.veil.android;

import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.media.projection.MediaProjectionManager;
import android.net.Uri;
import android.os.*;
import android.provider.Settings;
import android.view.*;
import android.widget.*;

public final class MainActivity extends Activity {
    private static final int CAPTURE=10,NOTIFICATIONS=11,PICK_MASK=12;
    private Prefs prefs;
    private TextView status,stats;
    private Button start;
    private int selected;
    private StyleSettingsView styleSettings;
    private boolean categoriesExpanded,advancedExpanded;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final Runnable refresh=new Runnable(){public void run(){
        if(status!=null)status.setText(ProtectionService.status);
        if(stats!=null)stats.setText(ProtectionService.frames+" frames checked   ·   "+ProtectionService.lastMs+" ms last scan");
        if(start!=null)start.setText(ProtectionService.running?"Stop Protection":"Start Protection");
        handler.postDelayed(this,800);
    }};
    @Override public void onCreate(Bundle saved){super.onCreate(saved);prefs=new Prefs(this);if(saved!=null){categoriesExpanded=saved.getBoolean("categoriesExpanded");advancedExpanded=saved.getBoolean("advancedExpanded");}showTab(saved==null?getIntent().getIntExtra("tab",0):saved.getInt("tab",0));}
    @Override protected void onNewIntent(Intent intent){super.onNewIntent(intent);setIntent(intent);showTab(intent.getIntExtra("tab",0));}
    @Override protected void onSaveInstanceState(Bundle state){state.putInt("tab",selected);state.putBoolean("categoriesExpanded",categoriesExpanded);state.putBoolean("advancedExpanded",advancedExpanded);super.onSaveInstanceState(state);}
    private void showTab(int tab){
        if(tab==2||tab==4){stopService(new Intent(this,ProtectionService.class));startActivity(new Intent(this,tab==2?BrowserActivity.class:PhotoActivity.class));return;}
        selected=tab==1||tab==3?tab:0;status=null;stats=null;start=null;styleSettings=null;
        LinearLayout root=Ui.column(this);root.addView(Ui.navigation(this,selected,this::showTab));
        ScrollView scroll=new ScrollView(this){@Override protected void onSizeChanged(int w,int h,int oldw,int oldh){super.onSizeChanged(w,h,oldw,oldh);if(getChildCount()>0){android.widget.FrameLayout.LayoutParams lp=(android.widget.FrameLayout.LayoutParams)getChildAt(0).getLayoutParams();lp.width=Math.min(w,Ui.dp(MainActivity.this,600));lp.gravity=Gravity.CENTER_HORIZONTAL;getChildAt(0).setLayoutParams(lp);}}};scroll.setFillViewport(false);scroll.setTag("main-scroll");
        LinearLayout content=Ui.column(this);int p=Ui.dp(this,16);content.setPadding(p,0,p,p);scroll.addView(content);
        root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
        if(selected==0)home(content);else if(selected==1)settings(content);else help(content);
        Ui.install(this,root);
    }
    private LinearLayout section(LinearLayout parent,String title,String description){
        LinearLayout c=Ui.card(this);c.addView(Ui.text(this,title,18,Ui.TEXT));
        if(description!=null)c.addView(Ui.text(this,description,14,Ui.MUTED));parent.addView(c);return c;
    }
    private void home(LinearLayout content){
        LinearLayout capture=section(content,"Screen Capture Protection","Start or stop the screen capture service.");
        start=Ui.button(this,ProtectionService.running?"Stop Protection":"Start Protection",Ui.GREEN,Ui.BG,()->{
            if(ProtectionService.running)stopService(new Intent(this,ProtectionService.class));else begin();
        });capture.addView(start);
        LinearLayout ai=section(content,"AI Censoring","Detect and censor the categories you choose.");
        ai.addView(Ui.check(this,"Enable AI detection",prefs.enabled(),b->{prefs.bool("enabled",b);if(!b)stopService(new Intent(this,ProtectionService.class));}));
        ai.addView(Ui.outline(this,"Censor style: "+prefs.styleName(),()->showTab(1)));
        ai.addView(Ui.text(this,"Quick toggles",13,Ui.TEXT));
        LinearLayout row=new LinearLayout(this);
        row.addView(Ui.check(this,"Invert censor",prefs.invert(),b->prefs.bool("invert",b)),new LinearLayout.LayoutParams(0,-2,1));
        row.addView(Ui.check(this,"Show labels",prefs.labels(),b->prefs.bool("labels",b)),new LinearLayout.LayoutParams(0,-2,1));ai.addView(row);
        slider(ai,"Censor coverage","padding",-40,70,18,"%");
        LinearLayout performance=section(content,"Performance","Ultra scans as fast as the detector allows. Higher settings use more battery.");
        choice(performance,"preset",new String[]{"Low","Medium","High","Ultra"},1);
        LinearLayout session=section(content,"Session",null);
        status=Ui.text(this,ProtectionService.status,13,Ui.MUTED);session.addView(status);
        stats=Ui.text(this,"0 frames checked",12,Ui.MUTED);session.addView(stats);
        session.addView(Ui.text(this,"Use one-app capture. Detection can be delayed or miss content.",12,Ui.MUTED));
        TextView footer=Ui.text(this,"Veil 0.4  ·  On-device filtering",11,Ui.MUTED);footer.setGravity(Gravity.CENTER);content.addView(footer);
    }
    private void settings(LinearLayout content){
        styleSettings=new StyleSettingsView(this,()->startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("image/*").addCategory(Intent.CATEGORY_OPENABLE),PICK_MASK),this::presets);
        content.addView(styleSettings);
        LinearLayout categoryCard=Ui.card(this);content.addView(categoryCard);
        LinearLayout categories=Ui.column(this);categories.setTag("category-options");
        Button categoryToggle=Ui.outline(this,"",()->{categoriesExpanded=!categoriesExpanded;showExpanded(categories,categoriesExpanded,"Detection categories");});
        categories.setVisibility(categoriesExpanded?View.VISIBLE:View.GONE);categories.setContentDescription("Detection categories");
        categoryToggle.setTag("category-toggle");categoryCard.addView(categoryToggle);categoryCard.addView(categories);
        showExpanded(categories,categoriesExpanded,"Detection categories");
        categories.addView(Ui.text(this,"Choose what Veil detects. Your selections are saved.",13,Ui.MUTED));
        String[] names={"Genitals (F)","Genitals (M)","Breasts (Female)","Buttocks","Anus","Genitals (Covered)","Breasts (Covered)","Buttocks (Covered)","Anus (Covered)","All Faces","Chest (Male)","Belly/Stomach","Feet","Armpits"};
        int[] bits={1<<4,1<<14,1<<3,1<<2,1<<6,1,1<<16,1<<17,1<<15,(1<<1)|(1<<12),1<<5,(1<<8)|(1<<13),(1<<7)|(1<<9),(1<<10)|(1<<11)};
        for(int i=0;i<names.length;i+=2){LinearLayout row=new LinearLayout(this);
            for(int j=i;j<Math.min(i+2,names.length);j++){final int mask=bits[j];
                row.addView(Ui.check(this,names[j],(prefs.mask()&mask)!=0,on->prefs.put("mask",on?prefs.mask()|mask:prefs.mask()&~mask)),new LinearLayout.LayoutParams(0,-2,1));
            }categories.addView(row);
        }
        LinearLayout advancedCard=Ui.card(this);content.addView(advancedCard);
        LinearLayout detection=Ui.column(this);detection.setTag("advanced-options");
        Button advancedToggle=Ui.outline(this,"",()->{advancedExpanded=!advancedExpanded;showExpanded(detection,advancedExpanded,"Advanced detection");});advancedToggle.setTag("advanced-toggle");
        advancedCard.addView(advancedToggle);advancedCard.addView(detection);showExpanded(detection,advancedExpanded,"Advanced detection");
        slider(detection,"Confidence threshold","confidence",20,90,45,"%");
        slider(detection,"Screen vertical adjustment","offset",-120,120,0," dp");
        detection.addView(Ui.text(this,"Lower confidence catches more with more false positives. Vertical adjustment aligns full-screen capture.",13,Ui.MUTED));
    }
    private void showExpanded(LinearLayout body,boolean expanded,String title){
        body.setVisibility(expanded?View.VISIBLE:View.GONE);
        Button toggle=(Button)((LinearLayout)body.getParent()).getChildAt(0);
        toggle.setText(title+(expanded?"  −":"  +"));
        toggle.setContentDescription(title+(expanded?", expanded":", collapsed"));
    }
    private void help(LinearLayout content){
        LinearLayout permission=section(content,"Permissions & battery","Appear-on-top permission lets Veil draw censor regions. Android asks for screen capture approval for each session.");
        permission.addView(Ui.button(this,"Overlay Settings",()->startActivity(new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,Uri.parse("package:"+getPackageName())))));
        permission.addView(Ui.button(this,"Battery Settings",()->startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,Uri.parse("package:"+getPackageName())))));
        LinearLayout guide=section(content,"Quick guide","1. Tap Start Protection on Home.\n2. Choose one app in Android’s capture dialog.\n3. Keep the app full screen.\n4. Pick your categories and censor style in Settings.");
        guide.addView(Ui.text(this,"Censor regions absorb touches. In crowded scenes, transparent gaps inside grouped windows also absorb touches. Scroll outside the groups. Box outline is a preview style; it leaves content visible. Invert hides the surrounding screen.",13,Ui.MUTED));
        LinearLayout tips=section(content,"If something looks wrong","Stop protection and start a new capture session. For offset boxes, try the vertical adjustment slider. Split screen and protected video are unsupported.");
        tips.addView(Ui.text(this,"The built-in browser filters page images. Hardware video and WebGL may remain unfiltered. No filter can guarantee every region is caught.",13,Ui.MUTED));
        LinearLayout privacy=section(content,"Privacy","Detection stays on your phone. No accounts, telemetry, uploads, or automatic recording. Browser websites receive normal browsing traffic and can store cookies.");
        privacy.addView(Ui.text(this,"Veil is an independent app. Language: English. Detection may miss content; review coverage for your setup.",12,Ui.MUTED));
    }
    private void presets(){new AlertDialog.Builder(this).setTitle("Style presets").setItems(new String[]{"Classic black","Pink labels","Purple pattern","Detection outline"},(d,n)->{
        prefs.put("style",new int[]{0,2,1,3}[n]);prefs.put("color",new int[]{0,1,2,3}[n]);prefs.bool("labels",n==1);if(styleSettings!=null)styleSettings.refresh();else showTab(1);
    }).setNegativeButton("Cancel",null).show();}
    private void begin(){
        if(prefs.mask()==0){Ui.message(this,"Choose at least one detection category first.");return;}
        if(!prefs.enabled()){prefs.bool("enabled",true);showTab(0);}
        if(!Settings.canDrawOverlays(this)){
            new AlertDialog.Builder(this).setTitle("Allow censor boxes").setMessage("Enable ‘Appear on top’ for Veil, then return and tap Start Protection again.")
                .setPositiveButton("Open settings",(d,w)->startActivity(new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,Uri.parse("package:"+getPackageName())))).setNegativeButton("Cancel",null).show();return;
        }
        if(checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED&&!prefs.p.getBoolean("notificationAsked",false)){
            prefs.p.edit().putBoolean("notificationAsked",true).apply();requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},NOTIFICATIONS);return;
        }
        new AlertDialog.Builder(this).setTitle("Choose one app").setMessage("Select a single app in Android’s next dialog and keep it full screen. Entire-screen capture can recapture the censor boxes and is unsupported.\n\nStop anytime from Veil, the notification, or Android’s capture indicator.")
            .setPositiveButton("Continue",(d,w)->startActivityForResult(getSystemService(MediaProjectionManager.class).createScreenCaptureIntent(),CAPTURE)).setNegativeButton("Cancel",null).show();
    }
    @Override public void onRequestPermissionsResult(int req,String[] permissions,int[] results){super.onRequestPermissionsResult(req,permissions,results);if(req==NOTIFICATIONS)begin();}
    @Override protected void onActivityResult(int req,int result,Intent data){super.onActivityResult(req,result,data);
        if(req==PICK_MASK&&result==RESULT_OK&&data!=null&&data.getData()!=null){
            Uri uri=data.getData();Toast.makeText(this,"Importing image…",Toast.LENGTH_SHORT).show();
            new Thread(()->{try{CustomMaskImage.importImage(getApplicationContext(),uri);prefs.put("style",4);handler.post(()->{if(!isDestroyed()&&!isFinishing()){if(styleSettings!=null)styleSettings.refresh();else showTab(1);}});}
                catch(Exception e){handler.post(()->{if(!isDestroyed())Ui.message(this,"Could not import image. Try a PNG or JPEG.");});}},"Veil image import").start();return;
        }
        if(req==CAPTURE&&result==RESULT_OK&&data!=null){try{startForegroundService(new Intent(this,ProtectionService.class).putExtra("code",result).putExtra("capture",data));}catch(RuntimeException e){Ui.message(this,"Could not start protection: "+e.getClass().getSimpleName());}}}
    private void choice(LinearLayout parent,String key,String[] labels,int def){
        Spinner s=new Spinner(this);s.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,labels));s.setSelection(Math.max(0,Math.min(labels.length-1,prefs.p.getInt(key,def))));s.setMinimumHeight(Ui.dp(this,48));
        s.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){public void onItemSelected(AdapterView<?> p,View v,int n,long id){prefs.put(key,n);}public void onNothingSelected(AdapterView<?> p){}});parent.addView(s);
    }
    private void slider(LinearLayout parent,String name,String key,int min,int max,int def,String suffix){
        TextView label=Ui.text(this,name+": "+prefs.p.getInt(key,def)+suffix,13,Ui.MUTED);parent.addView(label);
        SeekBar bar=new SeekBar(this);bar.setProgressTintList(android.content.res.ColorStateList.valueOf(Ui.PINK));bar.setThumbTintList(android.content.res.ColorStateList.valueOf(Ui.PINK));bar.setMax(max-min);bar.setProgress(prefs.p.getInt(key,def)-min);bar.setMinimumHeight(Ui.dp(this,42));
        bar.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){public void onProgressChanged(SeekBar s,int n,boolean user){if(user){prefs.put(key,n+min);label.setText(name+": "+(n+min)+suffix);}}public void onStartTrackingTouch(SeekBar s){}public void onStopTrackingTouch(SeekBar s){}});parent.addView(bar);
    }
    @Override protected void onResume(){super.onResume();handler.removeCallbacks(refresh);handler.post(refresh);}
    @Override protected void onPause(){handler.removeCallbacks(refresh);super.onPause();}
}
