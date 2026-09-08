package dev.veil.android;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/** Android-independent postprocessing. Coordinates are source-image pixels. */
public final class DetectionCore {
    private DetectionCore() {}
    public static final String[] LABELS = {
        "Covered genitals (female)", "Face (female)", "Exposed buttocks",
        "Exposed breasts (female)", "Exposed genitals (female)", "Exposed chest (male)",
        "Exposed anus", "Exposed feet", "Covered belly", "Covered feet",
        "Covered armpits", "Exposed armpits", "Face (male)", "Exposed belly",
        "Exposed genitals (male)", "Covered anus", "Covered breasts (female)", "Covered buttocks"
    };
    public static final int DEFAULT_MASK = (1<<2)|(1<<3)|(1<<4)|(1<<6)|(1<<14);
    public static final class Box {
        public final float left, top, right, bottom, score;
        public final int category;
        public Box(float l, float t, float r, float b, float s, int c) {
            left=l; top=t; right=r; bottom=b; score=s; category=c;
        }
        public Box expand(float ratio, int width, int height) {
            float dx=(right-left)*ratio, dy=(bottom-top)*ratio;
            return new Box(Math.max(0,left-dx),Math.max(0,top-dy),
                    Math.min(width,right+dx),Math.min(height,bottom+dy),score,category);
        }
    }
    public static List<Box> decode(float[][] output, int width, int height, float threshold, int mask) {
        if (width<=0 || height<=0) throw new IllegalArgumentException("Invalid image size");
        boolean channelsFirst=output.length==22;
        if (!channelsFirst && (output.length==0 || output[0].length!=22))
            throw new IllegalArgumentException("Expected NudeNet output [22,N] or [N,22]");
        int count=channelsFirst?output[0].length:output.length;
        for (float[] row:output) if (row.length!=(channelsFirst?count:22))
            throw new IllegalArgumentException("Ragged model output");
        float scale=Math.max(width,height)/320f;
        List<Box> boxes=new ArrayList<>();
        for(int i=0;i<count;i++) {
            int cls=0; float score=-1;
            for(int c=0;c<18;c++) {
                float s=at(output,channelsFirst,i,c+4);
                if(s>score) { score=s; cls=c; }
            }
            if(!Float.isFinite(score) || score<threshold || (mask&(1<<cls))==0) continue;
            float cx=at(output,channelsFirst,i,0)*scale, cy=at(output,channelsFirst,i,1)*scale;
            float w=at(output,channelsFirst,i,2)*scale, h=at(output,channelsFirst,i,3)*scale;
            if(!Float.isFinite(cx)||!Float.isFinite(cy)||!Float.isFinite(w)||!Float.isFinite(h)||w<=0||h<=0) continue;
            float l=Math.max(0,cx-w/2), t=Math.max(0,cy-h/2);
            float r=Math.min(width,cx+w/2), b=Math.min(height,cy+h/2);
            if(r>l && b>t) boxes.add(new Box(l,t,r,b,score,cls));
        }
        boxes.sort(Comparator.comparingDouble((Box b)->b.score).reversed());
        List<Box> kept=new ArrayList<>();
        for(Box box:boxes) {
            boolean suppress=false;
            for(Box prior:kept) if(prior.category==box.category && iou(prior,box)>.45f) { suppress=true; break; }
            if(!suppress) kept.add(box);
            if(kept.size()==32) break;
        }
        return kept;
    }
    private static float at(float[][] a,boolean cf,int i,int c) { return cf?a[c][i]:a[i][c]; }
    public static float iou(Box a, Box b) {
        float intersection=Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left))*
                Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top));
        float union=(a.right-a.left)*(a.bottom-a.top)+(b.right-b.left)*(b.bottom-b.top)-intersection;
        return union>0?intersection/union:0;
    }
}
