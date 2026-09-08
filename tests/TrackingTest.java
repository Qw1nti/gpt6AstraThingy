package dev.veil.android;
import java.util.*;

public final class TrackingTest {
    private static int checks;
    private static void check(boolean ok,String message){if(!ok)throw new AssertionError(message);checks++;}
    private static DetectionCore.Box box(float x,float y){return new DetectionCore.Box(x,y,x+40,y+60,.9f,3);}
    public static void main(String[] args){
        float[][] dense=new float[22][100];
        for(int i=0;i<100;i++){dense[0][i]=10+(i%10)*30;dense[1][i]=10+(i/10)*30;dense[2][i]=10;dense[3][i]=10;dense[7][i]=.9f;}
        List<DetectionCore.Box> boxes=DetectionCore.decode(dense,320,320,.45f,DetectionCore.DEFAULT_MASK);
        check(boxes.size()==100,"all dense-scene detections retained");
        List<List<DetectionCore.Box>> groups=RegionGroups.group(boxes,320,320);
        check(groups.size()<=16,"crowded windows bounded");
        Set<DetectionCore.Box> seen=Collections.newSetFromMap(new IdentityHashMap<>());
        for(List<DetectionCore.Box> g:groups){
            DetectionCore.Box bounds=RegionGroups.bounds(g);
            for(DetectionCore.Box b:g){check(seen.add(b),"no duplicated region");check(bounds.left<=b.left&&bounds.top<=b.top&&bounds.right>=b.right&&bounds.bottom>=b.bottom,"group encloses original region");}
        }
        check(seen.size()==boxes.size(),"no lost regions in grouping");
        check(RegionGroups.group(Collections.emptyList(),320,320).isEmpty(),"empty scene");
        DetectionCore.Box contracted=box(20,30).expand(-.4f,320,320);
        check(Math.abs((contracted.right-contracted.left)-8)<.001f,"negative coverage shrinks width to 20%");
        check(Math.abs((contracted.bottom-contracted.top)-12)<.001f,"negative coverage shrinks height to 20%");
        check(contracted.left>20&&contracted.top>30,"contraction inset");
        DetectionCore.Box bounded=box(0,0).expand(-100,320,320);
        check(bounded.right>bounded.left&&bounded.bottom>bounded.top,"extreme contraction cannot invert a box");
        MotionTracker tracker=new MotionTracker();
        tracker.update(Collections.singletonList(box(20,30)),320,320,1000);
        tracker.update(Collections.singletonList(box(26,30)),320,320,1060);
        DetectionCore.Box predicted=tracker.snapshot(1120).get(0);
        check(predicted.left>26&&predicted.left<=34,"short forward prediction bounded by box size");
        check(tracker.snapshot(2000).get(0).left<=34,"prediction cannot drift indefinitely");
        tracker.update(Collections.emptyList(),320,320,1100);
        check(tracker.snapshot(1120).size()==1,"brief missed detection held");
        tracker.update(Collections.emptyList(),320,320,1220);
        check(tracker.snapshot(1220).isEmpty(),"missed detection expires");
        tracker.update(Collections.singletonList(box(20,30)),320,320,1300);
        tracker.update(Collections.emptyList(),640,320,1360);
        check(tracker.snapshot(1360).isEmpty(),"resize clears prior coordinates");
        tracker.update(Collections.singletonList(box(20,30)),640,320,1400);
        tracker.clear();check(tracker.snapshot(1450).isEmpty(),"explicit lifecycle reset");
        tracker.update(boxes,320,320,2000);check(tracker.snapshot(2060).size()==100,"tracker preserves dense scenes");
        List<DetectionCore.Box> reverse=new ArrayList<>(boxes);Collections.reverse(reverse);
        tracker.update(reverse,320,320,2060);check(tracker.snapshot(2090).size()==100,"reordered detections matched once");
        System.out.println("PASS: "+checks+" dense-scene, grouping, coverage and tracking checks");
    }
}
