package dev.veil.android;
import android.content.Context;
import android.content.SharedPreferences;
final class Prefs {
    static final String[] STYLES={"Solid","Diagonal pattern","Labeled","Box outline","Custom image","Pixelated + border"};
    final SharedPreferences p;
    private final float density;
    Prefs(Context c){p=c.getSharedPreferences("veil",Context.MODE_PRIVATE);density=c.getResources().getDisplayMetrics().density;}
    int mask(){return p.getInt("mask",DetectionCore.DEFAULT_MASK)&((1<<18)-1);}
    float confidence(){return Math.max(.2f,Math.min(.9f,p.getInt("confidence",45)/100f));}
    float padding(){return Math.max(-.4f,Math.min(.7f,p.getInt("padding",18)/100f));}
    int interval(){return new int[]{350,150,66,0}[Math.max(0,Math.min(3,p.getInt("preset",1)))];}
    int color(){return new int[]{0xFF000000,0xFFFF0095,0xFFB18AF0,0xFFB9F45A}[Math.max(0,Math.min(3,p.getInt("color",0)))];}
    int style(){return Math.max(0,Math.min(STYLES.length-1,p.getInt("style",0)));}
    int pixelSize(){return Math.max(8,Math.min(64,p.getInt("pixelSize",24)));}
    float borderWidth(){return 3*density;}
    int borderColor(){return new int[]{0xFFFF0095,0xFFB9F45A,0xFFFFFFFF,0xFFB18AF0}[Math.max(0,Math.min(3,p.getInt("borderColor",0)))];}
    String styleName(){return STYLES[style()];}
    int offset(){return Math.max(-120,Math.min(120,p.getInt("offset",0)));}
    boolean invert(){return p.getBoolean("invert",false);}
    boolean labels(){return p.getBoolean("labels",false);}
    boolean enabled(){return p.getBoolean("enabled",true);}
    String label(){String text=p.getString("label","CENSORED");return text==null?"CENSORED":text.substring(0,Math.min(text.length(),32));}
    void put(String key,int value){p.edit().putInt(key,value).apply();}
    void bool(String key,boolean value){p.edit().putBoolean(key,value).apply();}
}
