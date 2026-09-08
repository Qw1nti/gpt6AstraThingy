package dev.veil.android;

import android.content.Context;
import android.graphics.*;
import android.view.*;
import java.util.*;

/** Main-thread only. Opaque, touchable regions avoid Android's untrusted pass-through restrictions. */
final class OverlayController {
    private final Context context;
    private final WindowManager wm;
    private final Prefs prefs;
    private final List<MaskView> views=new ArrayList<>();
    OverlayController(Context c) { context=c; wm=c.getSystemService(WindowManager.class); prefs=new Prefs(c); }
    void show(List<DetectionCore.Box> boxes,int captureWidth,int captureHeight) {
        boxes=MaskRegions.resolve(boxes,captureWidth,captureHeight,prefs.invert());
        Rect screen=wm.getMaximumWindowMetrics().getBounds();
        float scale=Math.min(screen.width()/(float)captureWidth,screen.height()/(float)captureHeight);
        float left=(screen.width()-captureWidth*scale)/2;
        float top=(screen.height()-captureHeight*scale)/2+Ui.dp(context,prefs.offset());
        while(views.size()>boxes.size()) removeLast();
        for(int i=0;i<boxes.size();i++) {
            DetectionCore.Box b=boxes.get(i);
            int x=Math.max(0,Math.min(screen.width()-1,Math.round(left+b.left*scale)));
            int y=Math.max(0,Math.min(screen.height()-1,Math.round(top+b.top*scale)));
            int r=Math.max(x+1,Math.min(screen.width(),Math.round(left+b.right*scale)));
            int bottom=Math.max(y+1,Math.min(screen.height(),Math.round(top+b.bottom*scale)));
            WindowManager.LayoutParams p=new WindowManager.LayoutParams(r-x,bottom-y,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE|WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL|
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,PixelFormat.TRANSLUCENT);
            p.gravity=Gravity.TOP|Gravity.LEFT; p.x=x; p.y=y;
            p.layoutInDisplayCutoutMode=WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS;
            p.setFitInsetsTypes(0);
            p.setTitle("Veil censor region");
            if(i==views.size()) {
                MaskView view=new MaskView(context); view.region();
                view.setOnTouchListener((v,event)->true);
                wm.addView(view,p); views.add(view);
            } else { wm.updateViewLayout(views.get(i),p); views.get(i).invalidate(); }
        }
    }
    private void removeLast() {
        MaskView view=views.remove(views.size()-1);
        try { wm.removeViewImmediate(view); } catch(IllegalArgumentException ignored) {}
    }
    void clear() { while(!views.isEmpty()) removeLast(); }
}
