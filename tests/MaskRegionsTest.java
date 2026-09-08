package dev.veil.android;
import java.util.*;
public final class MaskRegionsTest {
    private static int checks;
    private static DetectionCore.Box b(float l,float t,float r,float bottom){return new DetectionCore.Box(l,t,r,bottom,1,3);}
    private static void check(boolean value,String label){if(!value)throw new AssertionError(label);checks++;}
    private static boolean inside(DetectionCore.Box b,float x,float y){return x>=b.left&&x<b.right&&y>=b.top&&y<b.bottom;}
    private static double area(List<DetectionCore.Box> regions){double sum=0;for(var b:regions)sum+=(b.right-b.left)*(b.bottom-b.top);return sum;}
    public static void main(String[] args){
        check(area(MaskRegions.resolve(List.of(),100,80,true))==8000,"empty detections cover whole screen");
        check(MaskRegions.resolve(List.of(b(0,0,100,80)),100,80,true).isEmpty(),"full detection reveals whole screen");
        check(area(MaskRegions.resolve(List.of(b(20,20,80,60)),100,80,true))==5600,"center hole area");
        check(area(MaskRegions.resolve(List.of(b(-20,-20,50,40)),100,80,true))==6000,"clipped hole area");
        check(area(MaskRegions.resolve(List.of(b(150,150,160,160)),100,80,true))==8000,"outside hole ignored");
        check(area(MaskRegions.resolve(List.of(b(Float.NaN,0,30,30)),100,80,true))==8000,"NaN region ignored");
        List<DetectionCore.Box> original=new ArrayList<>(List.of(b(10,10,20,20)));
        List<DetectionCore.Box> normal=MaskRegions.resolve(original,100,80,false);normal.clear();check(original.size()==1,"normal mode independent list");
        Random random=new Random(41286);
        for(int scene=0;scene<50;scene++){
            List<DetectionCore.Box> holes=new ArrayList<>();for(int i=0;i<6;i++){int l=random.nextInt(100)-10,t=random.nextInt(80)-10;holes.add(b(l,t,l+random.nextInt(35)+1,t+random.nextInt(35)+1));}
            List<DetectionCore.Box> cover=MaskRegions.resolve(holes,100,80,true);
            for(var r:cover)check(r.left>=0&&r.top>=0&&r.right<=100&&r.bottom<=80&&r.left<r.right&&r.top<r.bottom,"bounded nonempty output");
            for(int y=0;y<80;y++)for(int x=0;x<100;x++){
                boolean detected=false;for(var hole:holes)detected|=inside(hole,x+.5f,y+.5f);
                int overlays=0;for(var r:cover)if(inside(r,x+.5f,y+.5f))overlays++;
                if(overlays!=(detected?0:1))throw new AssertionError("inverse coverage mismatch at scene "+scene+" pixel "+x+","+y);
            }
        }
        boolean invalid=false;try{MaskRegions.resolve(List.of(),0,10,true);}catch(IllegalArgumentException e){invalid=true;}check(invalid,"invalid surface rejected");
        List<DetectionCore.Box> complex=new ArrayList<>();for(int y=0;y<80;y+=8)for(int x=0;x<100;x+=8)complex.add(b(x+1,y+1,x+3,y+3));
        check(MaskRegions.resolve(complex,100,80,true).size()<=64,"complex scenes bound Android overlay count");
        System.out.println("PASS: inverse mask edge cases, "+checks+" geometry assertions and 50 randomized scenes / 400,000 coverage samples");
    }
}
