package dev.veil.android;

import android.content.Context;
import android.graphics.*;
import android.os.*;
import android.view.*;
import java.util.*;

/** Main-thread only. Windows are reused; crowded groups draw exact regions, including transparent gaps. */
final class OverlayController {
    private final Context context;
    private final WindowManager wm;
    private final Prefs prefs;
    private final Handler main=new Handler(Looper.getMainLooper());
    private final MotionTracker tracker=new MotionTracker();
    private final List<MaskView> views=new ArrayList<>();
    private final List<WindowManager.LayoutParams> layouts=new ArrayList<>();
    private int width=1,height=1,activeCount;
    private long sampleTime;
    private String settings="";
    private Bitmap pixels;
    private final Runnable animate=new Runnable(){public void run(){
        long now=SystemClock.elapsedRealtime();
        if(now-sampleTime>80||activeCount>12||prefs.invert())return;
        try{render(tracker.snapshot(now));main.postDelayed(this,33);}catch(RuntimeException e){clear();}
    }};
    OverlayController(Context c){context=c;wm=c.getSystemService(WindowManager.class);prefs=new Prefs(c);}
    void show(List<DetectionCore.Box> boxes,int captureWidth,int captureHeight,Bitmap texture,long timestamp){
        String current=prefs.mask()+":"+prefs.padding()+":"+prefs.confidence()+":"+prefs.invert();
        if(!current.equals(settings)){tracker.clear();settings=current;}
        width=captureWidth;height=captureHeight;pixels=texture;sampleTime=timestamp;
        tracker.update(boxes,width,height,timestamp);
        main.removeCallbacks(animate);render(tracker.snapshot(SystemClock.elapsedRealtime()));
        if(activeCount<=12&&!prefs.invert())main.postDelayed(animate,33);
    }
    private void render(List<DetectionCore.Box> tracked){
        List<List<DetectionCore.Box>> groups=RegionGroups.group(MaskRegions.resolve(tracked,width,height,prefs.invert()),width,height);
        Rect screen=wm.getMaximumWindowMetrics().getBounds();
        float scale=Math.min(screen.width()/(float)width,screen.height()/(float)height);
        float left=(screen.width()-width*scale)/2;
        float top=(screen.height()-height*scale)/2+Ui.dp(context,prefs.offset());
        activeCount=groups.size();
        for(int i=0;i<groups.size();i++){
            List<DetectionCore.Box> group=groups.get(i);DetectionCore.Box b=RegionGroups.bounds(group);
            int x=Math.max(0,Math.min(screen.width()-1,Math.round(left+b.left*scale)));
            int y=Math.max(0,Math.min(screen.height()-1,Math.round(top+b.top*scale)));
            int r=Math.max(x+1,Math.min(screen.width(),Math.round(left+b.right*scale)));
            int bottom=Math.max(y+1,Math.min(screen.height(),Math.round(top+b.bottom*scale)));
            DetectionCore.Box visibleBounds=new DetectionCore.Box((x-left)/scale,(y-top)/scale,(r-left)/scale,(bottom-top)/scale,1,-1);
            if(i==views.size()){
                WindowManager.LayoutParams p=new WindowManager.LayoutParams(r-x,bottom-y,WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                    WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE|WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL|WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,PixelFormat.TRANSLUCENT);
                p.gravity=Gravity.TOP|Gravity.LEFT;p.x=x;p.y=y;p.layoutInDisplayCutoutMode=WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS;p.setFitInsetsTypes(0);p.setTitle("Veil censor regions");
                MaskView view=new MaskView(context);
                // Consume touches on the actual masks. Gaps in grouped windows are noninteractive.
                view.setOnTouchListener((v,event)->true);
                wm.addView(view,p);views.add(view);layouts.add(p);
            }else{
                WindowManager.LayoutParams p=layouts.get(i);
                if(p.x!=x||p.y!=y||p.width!=r-x||p.height!=bottom-y){p.x=x;p.y=y;p.width=r-x;p.height=bottom-y;wm.updateViewLayout(views.get(i),p);}
            }
            MaskView view=views.get(i);view.setVisibility(View.VISIBLE);view.regions(group,visibleBounds,width,height,pixels);
        }
        for(int i=groups.size();i<views.size();i++)views.get(i).setVisibility(View.GONE);
    }
    void clear(){
        main.removeCallbacks(animate);tracker.clear();pixels=null;activeCount=0;
        for(MaskView view:views)try{wm.removeViewImmediate(view);}catch(IllegalArgumentException ignored){}
        views.clear();layouts.clear();
    }
}
