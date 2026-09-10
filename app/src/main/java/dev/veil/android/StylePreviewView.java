package dev.veil.android;

import android.content.Context;
import android.graphics.*;
import android.view.View;

/** A local, synthetic scene rendered with the same mask painter as photo export. */
final class StylePreviewView extends View {
    private final Prefs prefs;
    private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
    private Bitmap scene,pixels;
    StylePreviewView(Context context){
        super(context);prefs=new Prefs(context);
        setContentDescription("Simulated censor preview. This is not a detection test.");
        setBackground(Ui.shape(context,0xFF100D17,Ui.LINE,12));setClipToOutline(true);
    }
    void refresh(){
        if(scene==null)createScene();
        if(pixels!=null){pixels.recycle();pixels=null;}
        pixels=MaskView.pixelate(scene,prefs);invalidate();
    }
    private void createScene(){
        scene=Bitmap.createBitmap(320,180,Bitmap.Config.ARGB_8888);
        Canvas c=new Canvas(scene);Paint p=new Paint(Paint.ANTI_ALIAS_FLAG);
        c.drawColor(0xFF292234);
        p.setColor(0xFF756580);c.drawCircle(242,46,29,p);
        p.setColor(0xFF494156);c.drawRoundRect(18,98,113,171,12,12,p);
        p.setColor(0xFFB9F45A);c.drawCircle(68,61,14,p);
        p.setColor(0xFF8D7599);c.drawRoundRect(117,17,210,164,45,45,p);
        p.setColor(0xFFE0C5CF);c.drawCircle(163,53,24,p);
        p.setColor(0xFFBF839F);c.drawRoundRect(131,86,195,149,24,24,p);
        p.setColor(0xFF51405F);c.drawRoundRect(226,102,302,164,14,14,p);
    }
    @Override protected void onAttachedToWindow(){super.onAttachedToWindow();refresh();}
    @Override protected void onDetachedFromWindow(){
        if(pixels!=null)pixels.recycle();if(scene!=null)scene.recycle();pixels=null;scene=null;
        super.onDetachedFromWindow();
    }
    @Override protected void onDraw(Canvas canvas){
        super.onDraw(canvas);if(scene==null)return;
        paint.setStyle(Paint.Style.FILL);paint.setFilterBitmap(true);
        canvas.drawBitmap(scene,null,new RectF(0,0,getWidth(),getHeight()),paint);
        DetectionCore.Box box=new DetectionCore.Box(118,23,209,153,.95f,3).expand(prefs.padding(),320,180);
        Bitmap custom=prefs.style()==4?CustomMaskImage.load(getContext()):null;
        for(DetectionCore.Box region:MaskRegions.resolve(java.util.List.of(box),320,180,prefs.invert())){
            RectF rect=new RectF(region.left*getWidth()/320,region.top*getHeight()/180,region.right*getWidth()/320,region.bottom*getHeight()/180);
            MaskView.drawMask(canvas,rect,region,320,180,prefs,paint,pixels,custom);
        }
    }
}
