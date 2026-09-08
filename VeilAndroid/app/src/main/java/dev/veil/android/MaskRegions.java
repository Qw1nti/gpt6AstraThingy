package dev.veil.android;
import java.util.*;
/** Produces non-overlapping rectangles covering the complement of detected regions. */
public final class MaskRegions {
    private MaskRegions(){}
    public static List<DetectionCore.Box> resolve(List<DetectionCore.Box> detections,int width,int height,boolean invert){
        if(width<=0||height<=0)throw new IllegalArgumentException("Invalid canvas dimensions");
        if(!invert)return new ArrayList<>(detections);
        List<DetectionCore.Box> remaining=new ArrayList<>();remaining.add(rect(0,0,width,height));
        for(DetectionCore.Box cut:detections){
            if(!Float.isFinite(cut.left)||!Float.isFinite(cut.top)||!Float.isFinite(cut.right)||!Float.isFinite(cut.bottom))continue;
            List<DetectionCore.Box> next=new ArrayList<>();
            for(DetectionCore.Box source:remaining){
                float l=Math.max(source.left,cut.left),t=Math.max(source.top,cut.top),r=Math.min(source.right,cut.right),b=Math.min(source.bottom,cut.bottom);
                if(l>=r||t>=b){next.add(source);continue;}
                add(next,source.left,source.top,source.right,t);
                add(next,source.left,b,source.right,source.bottom);
                add(next,source.left,t,l,b);add(next,r,t,source.right,b);
            }
            // Bound the number of Android overlay windows. Complex scenes stay fully covered.
            if(next.size()>64)return Collections.singletonList(rect(0,0,width,height));
            remaining=next;
        }
        return remaining;
    }
    private static DetectionCore.Box rect(float l,float t,float r,float b){return new DetectionCore.Box(l,t,r,b,1,-1);}
    private static void add(List<DetectionCore.Box> target,float l,float t,float r,float b){if(r>l&&b>t)target.add(rect(l,t,r,b));}
}
