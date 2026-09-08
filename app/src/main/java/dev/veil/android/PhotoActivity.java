package dev.veil.android;

import android.app.Activity;
import android.content.Intent;
import android.graphics.*;
import android.net.Uri;
import android.os.*;
import android.widget.*;
import java.io.OutputStream;
import java.util.List;

public final class PhotoActivity extends Activity {
    private static final int PICK=20,SAVE=21;
    private ImageView preview;
    private TextView status;
    private Button export,pick;
    private HandlerThread thread;
    private Handler worker;
    private final Handler main=new Handler(Looper.getMainLooper());
    private Bitmap censored;
    private Detector detector;
    private volatile boolean destroyed;
    private boolean processing;
    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        thread=new HandlerThread("Veil photo detector"); thread.start(); worker=new Handler(thread.getLooper());
        LinearLayout root=Ui.column(this);root.addView(Ui.navigation(this,4,n->Ui.openTab(this,n)));
        LinearLayout header=Ui.card(this);LinearLayout.LayoutParams hp=new LinearLayout.LayoutParams(-1,-2);hp.setMargins(Ui.dp(this,16),0,Ui.dp(this,16),Ui.dp(this,12));header.setLayoutParams(hp);
        header.addView(Ui.text(this,"Export a censored image",16,Ui.TEXT));
        header.addView(Ui.text(this,"Select an image, review detections, and save a censored PNG.",14,Ui.MUTED));
        pick=Ui.button(this,"Choose photo",()->startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("image/*").addCategory(Intent.CATEGORY_OPENABLE),PICK));
        header.addView(pick);
        export=Ui.button(this,"Save PNG",()->{
            if(processing || censored==null) return;
            startActivityForResult(new Intent(Intent.ACTION_CREATE_DOCUMENT).setType("image/png")
                .addCategory(Intent.CATEGORY_OPENABLE).putExtra(Intent.EXTRA_TITLE,"veil-censored.png"),SAVE);
        }); export.setEnabled(false); header.addView(export);
        status=Ui.text(this,"Photos are processed on-device. Export resolution is limited to a 2048 px longest edge. Check for missed regions before sharing.",13,Ui.MUTED); header.addView(status);
        root.addView(header); preview=new ImageView(this); preview.setScaleType(ImageView.ScaleType.FIT_CENTER);
        root.addView(preview,new LinearLayout.LayoutParams(-1,0,1)); Ui.install(this,root);
    }
    @Override protected void onActivityResult(int request,int result,Intent intent) {
        super.onActivityResult(request,result,intent);
        if(result!=RESULT_OK||intent==null||intent.getData()==null) return;
        Uri uri=intent.getData();
        if(request==PICK && !processing) process(uri);
        else if(request==SAVE && censored!=null && !processing) save(uri);
    }
    private void setBusy(boolean busy) { processing=busy; pick.setEnabled(!busy); export.setEnabled(!busy&&censored!=null); }
    private void process(Uri uri) {
        setBusy(true); preview.setImageDrawable(null); status.setText("Checking photo locally…");
        worker.post(()->{
            Bitmap decoded=null,result=null;
            try {
                if(detector==null) detector=new Detector(this);
                decoded=ImageDecoder.decodeBitmap(ImageDecoder.createSource(getContentResolver(),uri),(decoder,info,source)->{
                    decoder.setAllocator(ImageDecoder.ALLOCATOR_SOFTWARE);
                    int w=info.getSize().getWidth(),h=info.getSize().getHeight();
                    float scale=Math.min(1f,2048f/Math.max(w,h));
                    decoder.setTargetSize(Math.max(1,Math.round(w*scale)),Math.max(1,Math.round(h*scale)));
                });
                Prefs prefs=new Prefs(this); List<DetectionCore.Box> boxes=detector.detect(decoded,prefs);
                result=decoded.copy(Bitmap.Config.ARGB_8888,true);
                Canvas canvas=new Canvas(result); Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
                Bitmap pixels=MaskView.pixelate(decoded,prefs),custom=prefs.style()==4?CustomMaskImage.load(this):null;
                for(DetectionCore.Box box:MaskRegions.resolve(boxes,result.getWidth(),result.getHeight(),prefs.invert())) MaskView.drawMask(canvas,new RectF(box.left,box.top,box.right,box.bottom),box,result.getWidth(),result.getHeight(),prefs,paint,pixels,custom);
                if(pixels!=null)pixels.recycle();
                Bitmap ready=result; result=null;
                main.post(()->{
                    if(destroyed) { ready.recycle(); return; }
                    Bitmap previous=censored; censored=ready; preview.setImageBitmap(censored);
                    if(previous!=null) previous.recycle();
                    status.setText(boxes.size()+" detections · "+ready.getWidth()+" × "+ready.getHeight()+"\n"+(prefs.style()==3?"Outline only — content remains visible.":"Review for missed regions before saving.")); setBusy(false);
                });
            } catch(Exception e) { main.post(()->{if(!destroyed) {
                if(censored!=null) { censored.recycle(); censored=null; }
                status.setText("Photo processing failed ("+e.getClass().getSimpleName()+"). Choose another image."); setBusy(false);
            }}); }
            finally { if(decoded!=null) decoded.recycle(); if(result!=null) result.recycle(); }
        });
    }
    private void save(Uri uri) {
        setBusy(true); Bitmap result=censored;
        worker.post(()->{
            String message;
            try(OutputStream out=getContentResolver().openOutputStream(uri,"wt")) {
                if(out==null || !result.compress(Bitmap.CompressFormat.PNG,100,out)) throw new java.io.IOException("Could not write image");
                message="Image saved. Original unchanged.";
            } catch(Exception e) { message="Could not save the image. Choose another destination."; }
            String text=message; main.post(()->{if(!destroyed) { status.setText(text); setBusy(false); }});
        });
    }
    @Override protected void onDestroy() {
        destroyed=true; preview.setImageDrawable(null); Bitmap old=censored; censored=null;
        worker.post(()->{
            if(old!=null) old.recycle();
            if(detector!=null) try { detector.close(); } catch(Exception ignored) {}
            thread.quitSafely();
        }); super.onDestroy();
    }
}
