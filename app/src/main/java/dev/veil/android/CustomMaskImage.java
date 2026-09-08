package dev.veil.android;

import android.content.Context;
import android.graphics.*;
import android.net.Uri;
import android.util.AtomicFile;
import java.io.*;

/** A bounded private copy survives restarts without keeping a document-provider permission. */
final class CustomMaskImage {
    private static Bitmap cached;
    private static boolean loaded;
    private static File file(Context c){return new File(c.getFilesDir(),"custom-mask.png");}
    static synchronized Bitmap load(Context c){
        if(!loaded){File f=file(c);cached=f.exists()?BitmapFactory.decodeFile(f.getPath()):null;loaded=true;}
        return cached;
    }
    static synchronized void importImage(Context c,Uri uri)throws IOException{
        Bitmap image=ImageDecoder.decodeBitmap(ImageDecoder.createSource(c.getContentResolver(),uri),(decoder,info,source)->{
            decoder.setAllocator(ImageDecoder.ALLOCATOR_SOFTWARE);
            float scale=Math.min(1f,512f/Math.max(info.getSize().getWidth(),info.getSize().getHeight()));
            decoder.setTargetSize(Math.max(1,Math.round(info.getSize().getWidth()*scale)),Math.max(1,Math.round(info.getSize().getHeight()*scale)));
        });
        AtomicFile target=new AtomicFile(file(c));FileOutputStream out=null;
        try{out=target.startWrite();if(!image.compress(Bitmap.CompressFormat.PNG,100,out))throw new IOException("Image encoding failed");target.finishWrite(out);out=null;cached=image;loaded=true;}
        catch(IOException|RuntimeException e){if(out!=null)target.failWrite(out);image.recycle();throw e;}
    }
    static synchronized void remove(Context c){new AtomicFile(file(c)).delete();cached=null;loaded=true;}
}
