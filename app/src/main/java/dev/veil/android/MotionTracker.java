package dev.veil.android;

import java.util.*;

/** Main-thread-owned short prediction. Never extrapolates more than 80 ms or 20% of box size. */
public final class MotionTracker {
    private static final long HOLD_MS=120, PREDICT_MS=80;
    private static final class Track {
        DetectionCore.Box box;
        float vx,vy;
        long seen;
        Track(DetectionCore.Box b,long time){box=b;seen=time;}
    }
    private final List<Track> tracks=new ArrayList<>();
    private int width,height;
    private long previousTime=-1;
    public void clear(){tracks.clear();previousTime=-1;}
    public void update(List<DetectionCore.Box> boxes,int w,int h,long time){
        if(w!=width||h!=height||time<=previousTime||time-previousTime>500)clear();
        width=w;height=h;previousTime=time;
        boolean[] used=new boolean[boxes.size()];
        Iterator<Track> it=tracks.iterator();
        while(it.hasNext()){
            Track track=it.next();int match=-1;float best=.05f;
            DetectionCore.Box predicted=position(track,time);
            for(int i=0;i<boxes.size();i++){
                DetectionCore.Box b=boxes.get(i);
                if(used[i]||b.category!=track.box.category)continue;
                float score=DetectionCore.iou(predicted,b);
                if(score>best){best=score;match=i;}
            }
            if(match<0){if(time-track.seen>HOLD_MS)it.remove();continue;}
            DetectionCore.Box b=boxes.get(match);used[match]=true;
            float dt=Math.max(1,time-track.seen);
            float vx=((b.left+b.right)-(track.box.left+track.box.right))/(2*dt);
            float vy=((b.top+b.bottom)-(track.box.top+track.box.bottom))/(2*dt);
            track.vx=.35f*track.vx+.65f*vx;track.vy=.35f*track.vy+.65f*vy;
            track.box=b;track.seen=time;
        }
        for(int i=0;i<boxes.size();i++)if(!used[i])tracks.add(new Track(boxes.get(i),time));
    }
    public List<DetectionCore.Box> snapshot(long now){
        List<DetectionCore.Box> result=new ArrayList<>(tracks.size());
        for(Track t:tracks){
            // Current-frame detections remain visible on a static captured screen.
            if(t.seen<previousTime&&now-t.seen>HOLD_MS)continue;
            result.add(position(t,now));
        }
        return result;
    }
    private DetectionCore.Box position(Track t,long now){
        DetectionCore.Box b=t.box;
        float dt=Math.max(0,Math.min(PREDICT_MS,now-t.seen));
        float dx=clamp(t.vx*dt,-(b.right-b.left)*.2f,(b.right-b.left)*.2f);
        float dy=clamp(t.vy*dt,-(b.bottom-b.top)*.2f,(b.bottom-b.top)*.2f);
        dx=clamp(dx,-b.left,width-b.right);dy=clamp(dy,-b.top,height-b.bottom);
        return new DetectionCore.Box(b.left+dx,b.top+dy,b.right+dx,b.bottom+dy,b.score,b.category);
    }
    private static float clamp(float x,float lo,float hi){return Math.max(lo,Math.min(hi,x));}
}
