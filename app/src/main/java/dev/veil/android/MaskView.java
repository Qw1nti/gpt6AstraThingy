package dev.veil.android;
import android.content.Context;
import android.graphics.*;
import android.view.View;
import java.util.*;
final class MaskView extends View {
    private final Paint p=new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Prefs prefs;
    private List<DetectionCore.Box> boxes=Collections.emptyList();
    private int sourceWidth=1,sourceHeight=1;
    private boolean entire;
    MaskView(Context c){super(c);prefs=new Prefs(c);setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_NO);}
    void fillEntire(){entire=true;invalidate();}
    void region(){boxes=Collections.singletonList(new DetectionCore.Box(0,0,1,1,1,-1));sourceWidth=1;sourceHeight=1;entire=false;invalidate();}
    void clear(){boxes=Collections.emptyList();entire=false;invalidate();}
    void update(List<DetectionCore.Box> b,int width,int height){boxes=MaskRegions.resolve(b,width,height,prefs.invert());sourceWidth=width;sourceHeight=height;entire=false;invalidate();}
    @Override protected void onDraw(Canvas c){super.onDraw(c);
        if(entire){p.setColor(Color.BLACK);p.setStyle(Paint.Style.FILL);c.drawRect(0,0,getWidth(),getHeight(),p);return;}
        for(DetectionCore.Box b:boxes)drawMask(c,new RectF(b.left*getWidth()/sourceWidth,b.top*getHeight()/sourceHeight,b.right*getWidth()/sourceWidth,b.bottom*getHeight()/sourceHeight),prefs,p);
    }
    static void drawMask(Canvas c,RectF r,Prefs prefs,Paint p){
        p.setStyle(Paint.Style.FILL);p.setColor(prefs.color());
        if(prefs.style()==3){p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(3);c.drawRect(r.left+1.5f,r.top+1.5f,r.right-1.5f,r.bottom-1.5f,p);p.setStyle(Paint.Style.FILL);return;}
        c.drawRect(r,p);
        if(prefs.style()==1){int save=c.save();c.clipRect(r);p.setColor(0xFF403548);p.setStrokeWidth(5);for(float x=r.left-r.height();x<r.right;x+=20)c.drawLine(x,r.top,x+r.height(),r.bottom,p);c.restoreToCount(save);}
        if((prefs.style()==2||prefs.labels())&&r.width()>40&&r.height()>18){
            String label=prefs.label();if(label.isEmpty())return;
            p.setColor(prefs.color()==Color.BLACK?Color.WHITE:Color.BLACK);p.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));p.setTextSize(24);p.setTextAlign(Paint.Align.CENTER);
            float measured=p.measureText(label);if(measured>0)p.setTextSize(Math.min(24,24*(r.width()-12)/measured));
            int save=c.save();c.clipRect(r);c.drawText(label,r.centerX(),r.centerY()-(p.ascent()+p.descent())/2,p);c.restoreToCount(save);
        }
    }
}
