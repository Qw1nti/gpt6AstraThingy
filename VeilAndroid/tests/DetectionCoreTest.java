package dev.veil.android;
import java.util.List;

public final class DetectionCoreTest {
    private static int count;
    private static void check(boolean value,String name) { if(!value) throw new AssertionError(name); count++; }
    private static boolean near(float a,float b) { return Math.abs(a-b)<.01f; }
    private static float[][] sample() {
        float[][] a=new float[22][1]; a[0][0]=100; a[1][0]=80; a[2][0]=40; a[3][0]=20; a[7][0]=.9f; return a;
    }
    public static void main(String[] args) {
        List<DetectionCore.Box> b=DetectionCore.decode(sample(),320,320,.45f,DetectionCore.DEFAULT_MASK);
        check(b.size()==1,"selected category detected");
        check(near(b.get(0).left,80)&&near(b.get(0).top,70)&&near(b.get(0).right,120),"center to corners");
        check(DetectionCore.decode(sample(),320,320,.95f,DetectionCore.DEFAULT_MASK).isEmpty(),"threshold");
        check(DetectionCore.decode(sample(),320,320,.45f,0).isEmpty(),"disabled categories");
        b=DetectionCore.decode(sample(),640,320,.45f,DetectionCore.DEFAULT_MASK);
        check(near(b.get(0).left,160)&&near(b.get(0).top,140),"landscape pad inversion");
        b=DetectionCore.decode(sample(),320,640,.45f,DetectionCore.DEFAULT_MASK);
        check(near(b.get(0).left,160)&&near(b.get(0).bottom,180),"portrait pad inversion");
        float[][] cf=sample(),transposed=new float[1][22]; for(int c=0;c<22;c++) transposed[0][c]=cf[c][0];
        check(DetectionCore.decode(transposed,320,320,.45f,DetectionCore.DEFAULT_MASK).size()==1,"transposed output");
        float[][] duplicate=new float[22][2]; for(int c=0;c<22;c++) duplicate[c][0]=duplicate[c][1]=cf[c][0];
        check(DetectionCore.decode(duplicate,320,320,.45f,DetectionCore.DEFAULT_MASK).size()==1,"same-class NMS");
        duplicate[7][1]=0; duplicate[6][1]=.95f;
        check(DetectionCore.decode(duplicate,320,320,.45f,DetectionCore.DEFAULT_MASK).size()==2,"different categories preserved");
        cf=sample(); cf[0][0]=900;
        check(DetectionCore.decode(cf,320,320,.45f,DetectionCore.DEFAULT_MASK).isEmpty(),"padding/outside filtered");
        cf=sample(); cf[0][0]=Float.NaN;
        check(DetectionCore.decode(cf,320,320,.45f,DetectionCore.DEFAULT_MASK).isEmpty(),"NaN rejected");
        cf=sample(); cf[2][0]=-10;
        check(DetectionCore.decode(cf,320,320,.45f,DetectionCore.DEFAULT_MASK).isEmpty(),"negative width rejected");
        cf=sample(); cf[0][0]=0;
        b=DetectionCore.decode(cf,320,320,.45f,DetectionCore.DEFAULT_MASK);
        check(near(b.get(0).left,0)&&near(b.get(0).right,20),"clip source edges");
        DetectionCore.Box expanded=new DetectionCore.Box(0,0,100,100,.9f,3).expand(.5f,120,120);
        check(expanded.left==0&&expanded.right==120&&expanded.bottom==120,"padding clamps");
        check(near(DetectionCore.iou(expanded,expanded),1),"self IoU");
        boolean invalid=false; try { DetectionCore.decode(new float[2][3],320,320,.4f,1); } catch(IllegalArgumentException e) { invalid=true; }
        check(invalid,"incompatible model rejected");
        invalid=false; cf=sample(); cf[5]=new float[2];
        try { DetectionCore.decode(cf,320,320,.4f,1); } catch(IllegalArgumentException e) { invalid=true; }
        check(invalid,"ragged output rejected");
        cf=sample(); cf[7][0]=Float.POSITIVE_INFINITY;
        check(DetectionCore.decode(cf,320,320,.45f,DetectionCore.DEFAULT_MASK).isEmpty(),"infinite score rejected");
        System.out.println("PASS: "+count+" detection geometry checks");
    }
}
