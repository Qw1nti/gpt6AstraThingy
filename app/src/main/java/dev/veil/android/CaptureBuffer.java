package dev.veil.android;

import android.graphics.*;
import android.media.Image;
import java.nio.ByteBuffer;

/** Worker-confined reusable buffers. The returned bitmap is valid until the next copy. */
final class CaptureBuffer implements AutoCloseable {
    private Bitmap padded,frame;
    private Canvas canvas;
    private ByteBuffer storage;
    private int[] fallback;
    Bitmap copy(Image image){
        Image.Plane plane=image.getPlanes()[0];
        int w=image.getWidth(),h=image.getHeight(),row=plane.getRowStride(),pixel=plane.getPixelStride();
        ByteBuffer bytes=plane.getBuffer().duplicate();
        if(frame==null||frame.getWidth()!=w||frame.getHeight()!=h){
            close();frame=Bitmap.createBitmap(w,h,Bitmap.Config.ARGB_8888);canvas=new Canvas(frame);
        }
        if(pixel==4&&row%4==0){
            int strideW=row/4;
            if(padded==null||padded.getWidth()!=strideW||padded.getHeight()!=h){
                if(padded!=null)padded.recycle();
                padded=Bitmap.createBitmap(strideW,h,Bitmap.Config.ARGB_8888);
                storage=ByteBuffer.allocateDirect(row*h);
            }
            storage.clear();
            int size=Math.min(bytes.remaining(),storage.capacity());bytes.limit(bytes.position()+size);
            storage.put(bytes);storage.position(0);storage.limit(storage.capacity());
            padded.copyPixelsFromBuffer(storage);
            canvas.drawBitmap(padded,new Rect(0,0,w,h),new Rect(0,0,w,h),null);
        }else{
            if(fallback==null||fallback.length!=w*h)fallback=new int[w*h];
            int base=bytes.position();
            for(int y=0;y<h;y++)for(int x=0;x<w;x++){
                int i=base+y*row+x*pixel;
                fallback[y*w+x]=0xFF000000|((bytes.get(i)&255)<<16)|((bytes.get(i+1)&255)<<8)|(bytes.get(i+2)&255);
            }
            frame.setPixels(fallback,0,w,0,0,w,h);
        }
        return frame;
    }
    @Override public void close(){if(padded!=null)padded.recycle();if(frame!=null)frame.recycle();padded=null;frame=null;canvas=null;storage=null;fallback=null;}
}
