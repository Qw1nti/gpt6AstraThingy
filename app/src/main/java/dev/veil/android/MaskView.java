package dev.veil.android;
import android.content.Context;
import android.graphics.*;
import android.view.View;
import java.util.*;

final class MaskView extends View {
    private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Prefs prefs;
    private List<DetectionCore.Box> boxes=Collections.emptyList();
    private int sourceWidth=1,sourceHeight=1;
    private float originX,originY,spanWidth=1,spanHeight=1;
    private Bitmap texture,custom;
    private boolean entire;
    MaskView(Context c){super(c);prefs=new Prefs(c);setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_NO);}
    void fillEntire(){entire=true;texture=null;invalidate();}
    void clear(){boxes=Collections.emptyList();entire=false;texture=null;invalidate();}
    void update(List<DetectionCore.Box> b,int width,int height){update(b,width,height,null);}
    void update(List<DetectionCore.Box> b,int width,int height,Bitmap pixels){
        regions(MaskRegions.resolve(b,width,height,prefs.invert()),new DetectionCore.Box(0,0,width,height,1,-1),width,height,pixels);
    }
    void regions(List<DetectionCore.Box> b,DetectionCore.Box bounds,int width,int height,Bitmap pixels){
        boxes=b;sourceWidth=width;sourceHeight=height;originX=bounds.left;originY=bounds.top;
        spanWidth=Math.max(1,bounds.right-bounds.left);spanHeight=Math.max(1,bounds.bottom-bounds.top);
        texture=pixels;custom=prefs.style()==4?CustomMaskImage.load(getContext()):null;entire=false;invalidate();
    }
    void scroll(int dx,int dy){
        if(getWidth()==0||getHeight()==0)return;
        float x=dx*spanWidth/getWidth(),y=dy*spanHeight/getHeight();
        List<DetectionCore.Box> moved=new ArrayList<>();
        for(DetectionCore.Box b:boxes){
            float l=Math.max(0,b.left+x),t=Math.max(0,b.top+y),r=Math.min(sourceWidth,b.right+x),bottom=Math.min(sourceHeight,b.bottom+y);
            if(r>l&&bottom>t)moved.add(new DetectionCore.Box(l,t,r,bottom,b.score,b.category));
        }
        boxes=moved;texture=null;invalidate();
    }
    @Override protected void onDraw(Canvas c){super.onDraw(c);
        if(entire){paint.setColor(Color.BLACK);paint.setStyle(Paint.Style.FILL);c.drawRect(0,0,getWidth(),getHeight(),paint);return;}
        for(DetectionCore.Box b:boxes){
            RectF dest=new RectF((b.left-originX)*getWidth()/spanWidth,(b.top-originY)*getHeight()/spanHeight,(b.right-originX)*getWidth()/spanWidth,(b.bottom-originY)*getHeight()/spanHeight);
            drawMask(c,dest,b,sourceWidth,sourceHeight,prefs,paint,texture,custom);
        }
    }
    /** Only a coarse image leaves the capture worker; full frames are never retained by views. */
    static Bitmap pixelate(Bitmap frame,Prefs prefs){
        if(prefs.style()!=5)return null;
        int w=Math.max(1,(frame.getWidth()+prefs.pixelSize()-1)/prefs.pixelSize());
        int h=Math.max(1,(frame.getHeight()+prefs.pixelSize()-1)/prefs.pixelSize());
        return Bitmap.createScaledBitmap(frame,w,h,true);
    }
    static void drawMask(Canvas c,RectF r,DetectionCore.Box box,int width,int height,Prefs prefs,Paint p,Bitmap pixels,Bitmap custom){
        p.setStyle(Paint.Style.FILL);p.setColor(prefs.color());p.setFilterBitmap(false);
        int style=prefs.style();
        if(style==3){border(c,r,p,prefs.color(),3);return;}
        // Opaque underlay also covers transparency in an imported image.
        if(style==4||style==5)p.setColor(Color.BLACK);
        c.drawRect(r,p);
        if(style==4&&custom!=null&&!custom.isRecycled()){
            float scale=Math.max(r.width()/custom.getWidth(),r.height()/custom.getHeight());
            float sw=r.width()/scale,sh=r.height()/scale;
            Rect src=new Rect(Math.max(0,(int)((custom.getWidth()-sw)/2)),Math.max(0,(int)((custom.getHeight()-sh)/2)),Math.min(custom.getWidth(),(int)Math.ceil((custom.getWidth()+sw)/2)),Math.min(custom.getHeight(),(int)Math.ceil((custom.getHeight()+sh)/2)));
            p.setFilterBitmap(true);c.drawBitmap(custom,src,r,p);p.setFilterBitmap(false);
        }
        if(style==5){
            if(pixels!=null&&!pixels.isRecycled()){
                int l=Math.max(0,Math.min(pixels.getWidth()-1,(int)Math.floor(box.left*pixels.getWidth()/width)));
                int t=Math.max(0,Math.min(pixels.getHeight()-1,(int)Math.floor(box.top*pixels.getHeight()/height)));
                int right=Math.max(l+1,Math.min(pixels.getWidth(),(int)Math.ceil(box.right*pixels.getWidth()/width)));
                int bottom=Math.max(t+1,Math.min(pixels.getHeight(),(int)Math.ceil(box.bottom*pixels.getHeight()/height)));
                c.drawBitmap(pixels,new Rect(l,t,right,bottom),r,p);
            }
            border(c,r,p,prefs.borderColor(),prefs.borderWidth());
        }
        if(style==1){int save=c.save();c.clipRect(r);p.setColor(0xFF403548);p.setStrokeWidth(5);for(float x=r.left-r.height();x<r.right;x+=20)c.drawLine(x,r.top,x+r.height(),r.bottom,p);c.restoreToCount(save);}
        if((style==2||prefs.labels())&&r.width()>40&&r.height()>18){
            String label=prefs.label();if(label.isEmpty())return;
            p.setColor(prefs.color()==Color.BLACK?Color.WHITE:Color.BLACK);p.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));p.setTextSize(24);p.setTextAlign(Paint.Align.CENTER);
            float measured=p.measureText(label);if(measured>0)p.setTextSize(Math.min(24,24*(r.width()-12)/measured));
            int save=c.save();c.clipRect(r);c.drawText(label,r.centerX(),r.centerY()-(p.ascent()+p.descent())/2,p);c.restoreToCount(save);
        }
    }
    private static void border(Canvas c,RectF r,Paint p,int color,float width){
        float stroke=Math.min(width,Math.min(r.width(),r.height())/2);
        p.setColor(color);p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(stroke);
        float inset=stroke/2;c.drawRect(r.left+inset,r.top+inset,r.right-inset,r.bottom-inset,p);p.setStyle(Paint.Style.FILL);
    }
}
