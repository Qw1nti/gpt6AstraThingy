package dev.veil.android;
import java.util.*;

/** Groups drawing regions without discarding detections or filling gaps between them. */
public final class RegionGroups {
    private RegionGroups(){}
    public static List<List<DetectionCore.Box>> group(List<DetectionCore.Box> boxes,int width,int height){
        List<List<DetectionCore.Box>> groups=new ArrayList<>();
        if(boxes.size()<=24){for(DetectionCore.Box b:boxes)groups.add(Collections.singletonList(b));return groups;}
        for(int i=0;i<16;i++)groups.add(new ArrayList<>());
        for(DetectionCore.Box b:boxes){
            int x=Math.max(0,Math.min(3,(int)((b.left+b.right)*2/Math.max(1,width))));
            int y=Math.max(0,Math.min(3,(int)((b.top+b.bottom)*2/Math.max(1,height))));
            groups.get(y*4+x).add(b);
        }
        groups.removeIf(List::isEmpty);return groups;
    }
    public static DetectionCore.Box bounds(List<DetectionCore.Box> boxes){
        float l=Float.POSITIVE_INFINITY,t=l,r=Float.NEGATIVE_INFINITY,b=r;
        for(DetectionCore.Box box:boxes){l=Math.min(l,box.left);t=Math.min(t,box.top);r=Math.max(r,box.right);b=Math.max(b,box.bottom);}
        return new DetectionCore.Box(l,t,r,b,1,-1);
    }
}
