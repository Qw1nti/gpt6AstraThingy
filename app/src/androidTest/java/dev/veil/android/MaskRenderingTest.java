package dev.veil.android;

import android.content.Context;
import android.graphics.*;
import android.net.Uri;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.*;
import org.junit.runner.RunWith;
import java.io.*;
import static org.junit.Assert.*;

@RunWith(AndroidJUnit4.class)
public final class MaskRenderingTest {
    private Context context;
    private Prefs prefs;
    @Before public void setup(){context=InstrumentationRegistry.getInstrumentation().getTargetContext();prefs=new Prefs(context);prefs.p.edit().clear().commit();CustomMaskImage.remove(context);}
    @After public void cleanup(){CustomMaskImage.remove(context);prefs.p.edit().clear().commit();}
    @Test public void pixelationUsesFramePixelsAndHighlightedBorder(){
        prefs.put("style",5);prefs.put("pixelSize",8);
        Bitmap source=Bitmap.createBitmap(64,64,Bitmap.Config.ARGB_8888);
        for(int y=0;y<64;y++)for(int x=0;x<64;x++)source.setPixel(x,y,(x+y)%2==0?Color.WHITE:Color.BLACK);
        Bitmap pixels=MaskView.pixelate(source,prefs),output=Bitmap.createBitmap(64,64,Bitmap.Config.ARGB_8888);
        output.eraseColor(Color.BLUE);
        DetectionCore.Box box=new DetectionCore.Box(16,16,48,48,1,3);
        MaskView.drawMask(new Canvas(output),new RectF(16,16,48,48),box,64,64,prefs,new Paint(),pixels,null);
        assertEquals(8,pixels.getWidth());assertEquals(8,pixels.getHeight());
        assertEquals(Color.BLUE,output.getPixel(0,0));
        assertEquals(prefs.borderColor(),output.getPixel(17,32));
        assertEquals(output.getPixel(32,32),output.getPixel(33,32));
        assertNotEquals(source.getPixel(32,32),source.getPixel(33,32));
        assertNotEquals(Color.BLUE,output.getPixel(32,32));
        assertNotEquals(Color.BLACK,output.getPixel(32,32));
        source.recycle();pixels.recycle();output.recycle();
    }
    @Test public void transparentCustomImageHasOpaqueBacking(){
        prefs.put("style",4);
        Bitmap custom=Bitmap.createBitmap(20,40,Bitmap.Config.ARGB_8888);
        Bitmap output=Bitmap.createBitmap(64,64,Bitmap.Config.ARGB_8888);output.eraseColor(Color.BLUE);
        DetectionCore.Box box=new DetectionCore.Box(8,8,56,56,1,3);
        MaskView.drawMask(new Canvas(output),new RectF(8,8,56,56),box,64,64,prefs,new Paint(),null,custom);
        assertEquals(Color.BLACK,output.getPixel(32,32));assertEquals(Color.BLUE,output.getPixel(0,0));
        custom.eraseColor(Color.GREEN);
        MaskView.drawMask(new Canvas(output),new RectF(8,8,56,56),box,64,64,prefs,new Paint(),null,custom);
        assertEquals(Color.GREEN,output.getPixel(32,32));
        custom.recycle();output.recycle();
    }
    @Test public void importedImageIsBoundedPrivateCopy()throws Exception{
        File input=new File(context.getCacheDir(),"mask-fixture.png");
        Bitmap source=Bitmap.createBitmap(1024,512,Bitmap.Config.ARGB_8888);source.eraseColor(Color.GREEN);
        try(OutputStream out=new FileOutputStream(input)){assertTrue(source.compress(Bitmap.CompressFormat.PNG,100,out));}
        CustomMaskImage.importImage(context,Uri.fromFile(input));
        assertTrue(input.delete());
        Bitmap saved=CustomMaskImage.load(context);
        assertNotNull(saved);assertEquals(512,saved.getWidth());assertEquals(256,saved.getHeight());assertEquals(Color.GREEN,saved.getPixel(10,10));
        assertTrue(new File(context.getFilesDir(),"custom-mask.png").isFile());
        CustomMaskImage.remove(context);assertNull(CustomMaskImage.load(context));source.recycle();
    }
    @Test public void captureBufferReusesBitmapAndPreservesRgba()throws Exception{
        android.os.HandlerThread thread=new android.os.HandlerThread("capture-test");thread.start();
        android.os.Handler handler=new android.os.Handler(thread.getLooper());
        android.media.ImageReader reader=android.media.ImageReader.newInstance(20,12,PixelFormat.RGBA_8888,2);
        android.media.ImageWriter writer=android.media.ImageWriter.newInstance(reader.getSurface(),2);
        CaptureBuffer buffer=new CaptureBuffer();Bitmap previous=null;
        try{
            for(int pass=0;pass<2;pass++){
                java.util.concurrent.CountDownLatch ready=new java.util.concurrent.CountDownLatch(1);
                reader.setOnImageAvailableListener(r->ready.countDown(),handler);
                android.media.Image input=writer.dequeueInputImage();
                android.media.Image.Plane plane=input.getPlanes()[0];java.nio.ByteBuffer bytes=plane.getBuffer();
                int base=bytes.position();
                for(int y=0;y<12;y++)for(int x=0;x<20;x++){
                    int offset=base+y*plane.getRowStride()+x*plane.getPixelStride();
                    bytes.put(offset,(byte)(pass==0?255:0));bytes.put(offset+1,(byte)(pass==1?255:0));bytes.put(offset+2,(byte)0);bytes.put(offset+3,(byte)255);
                }
                writer.queueInputImage(input);
                assertTrue("capture delivered",ready.await(5,java.util.concurrent.TimeUnit.SECONDS));
                try(android.media.Image image=reader.acquireLatestImage()){
                    assertNotNull(image);Bitmap copied=buffer.copy(image);
                    assertEquals(pass==0?Color.RED:Color.GREEN,copied.getPixel(19,11));
                    if(previous!=null)assertSame(previous,copied);previous=copied;
                }
            }
        }finally{buffer.close();writer.close();reader.close();thread.quitSafely();}
    }

}
