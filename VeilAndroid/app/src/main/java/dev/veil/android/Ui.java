package dev.veil.android;
import android.app.Activity;
import android.content.Context;
import android.graphics.*;
import android.content.res.ColorStateList;
import android.graphics.drawable.*;
import android.view.*;
import android.widget.*;
import java.util.function.IntConsumer;
final class Ui {
    static final int BG=0xFF11000F,CARD=0xFF191521,TEXT=0xFFECE9F0,MUTED=0xFFAAA2B1;
    static final int PINK=0xFFFF0095,GREEN=0xFFB9F45A,LINE=0xFF312939,MINT=PINK;
    static final String[] TABS={"Home","Settings","Browser","Help","Export"};
    static int dp(Context c,float n){return Math.round(n*c.getResources().getDisplayMetrics().density);}
    static LinearLayout column(Context c){LinearLayout v=new LinearLayout(c);v.setOrientation(LinearLayout.VERTICAL);return v;}
    static GradientDrawable shape(Context c,int fill,int stroke,int radius){GradientDrawable d=new GradientDrawable();d.setColor(fill);d.setCornerRadius(dp(c,radius));if(stroke!=0)d.setStroke(dp(c,1),stroke);return d;}
    static void install(Activity a,View root){
        root.setBackground(new GradientDrawable(GradientDrawable.Orientation.TL_BR,new int[]{0xFF180015,0xFF0C000B,0xFF180014}));
        root.setOnApplyWindowInsetsListener((v,w)->{Insets i=w.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout()|WindowInsets.Type.ime());v.setPadding(i.left,i.top,i.right,i.bottom);return w;});
        a.setContentView(root);root.requestApplyInsets();
    }
    static TextView text(Context c,String s,int size,int color){TextView t=new TextView(c);t.setText(s);t.setTextSize(size);t.setTextColor(color);t.setPadding(0,dp(c,4),0,dp(c,4));return t;}
    static TextView title(Context c,String s){TextView t=text(c,s,22,TEXT);t.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));return t;}
    static LinearLayout card(Context c){LinearLayout l=column(c);int p=dp(c,16);l.setPadding(p,p,p,p);l.setBackground(shape(c,CARD,0,15));LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.bottomMargin=dp(c,12);l.setLayoutParams(lp);return l;}
    static Button button(Context c,String s,Runnable action){return button(c,s,PINK,BG,action);}
    static Button button(Context c,String s,int fill,int ink,Runnable action){
        Button b=new Button(c);b.setText(s);b.setAllCaps(false);b.setTextColor(ink);b.setTextSize(16);b.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));b.setLetterSpacing(.06f);
        b.setBackground(new RippleDrawable(ColorStateList.valueOf(0x337F7F7F),shape(c,fill,0,5),null));b.setMinHeight(dp(c,48));b.setMinimumWidth(0);b.setMinWidth(0);b.setPadding(dp(c,10),dp(c,8),dp(c,10),dp(c,8));b.setOnClickListener(v->action.run());
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.topMargin=dp(c,10);b.setLayoutParams(lp);return b;
    }
    static Button outline(Context c,String s,Runnable action){Button b=button(c,s,Color.TRANSPARENT,GREEN,action);b.setBackground(shape(c,Color.TRANSPARENT,GREEN,5));return b;}
    static void gap(LinearLayout l,int size){View v=new View(l.getContext());l.addView(v,new LinearLayout.LayoutParams(1,dp(l.getContext(),size)));}
    static View navigation(Activity a,int selected,IntConsumer change){
        LinearLayout row=new LinearLayout(a);row.setGravity(Gravity.CENTER_VERTICAL);row.setBackground(shape(a,CARD,0,14));
        LinearLayout.LayoutParams outer=new LinearLayout.LayoutParams(-1,dp(a,68));outer.setMargins(dp(a,16),dp(a,16),dp(a,16),dp(a,20));row.setLayoutParams(outer);
        for(int i=0;i<TABS.length;i++){
            final int tab=i;LinearLayout item=column(a);item.setGravity(Gravity.CENTER);item.setPadding(0,dp(a,9),0,0);item.setContentDescription(TABS[i]);item.setFocusable(true);item.setClickable(true);item.setSelected(i==selected);item.setBackground(new RippleDrawable(ColorStateList.valueOf(0x22FF0095),null,null));
            item.addView(new Icon(a,i,i==selected?PINK:0xFF79727F),new LinearLayout.LayoutParams(dp(a,21),dp(a,21)));
            TextView label=text(a,TABS[i],11,i==selected?TEXT:0xFF938A9B);label.setGravity(Gravity.CENTER);item.addView(label,new LinearLayout.LayoutParams(-1,dp(a,27)));
            View underline=new View(a);underline.setBackgroundColor(i==selected?PINK:Color.TRANSPARENT);item.addView(underline,new LinearLayout.LayoutParams(-1,dp(a,2)));
            item.setOnClickListener(v->change.accept(tab));row.addView(item,new LinearLayout.LayoutParams(0,-1,1));
        }return row;
    }
    static CheckBox check(Context c,String label,boolean checked,java.util.function.Consumer<Boolean> action){CheckBox box=new CheckBox(c);box.setText(label);box.setTextSize(13);box.setTextColor(MUTED);box.setButtonTintList(ColorStateList.valueOf(PINK));box.setChecked(checked);box.setMinHeight(dp(c,40));box.setPadding(0,0,0,0);box.setOnCheckedChangeListener((v,b)->action.accept(b));return box;}
    static void openTab(Activity a,int tab){
        if((tab==2&&a instanceof BrowserActivity)||(tab==4&&a instanceof PhotoActivity))return;
        Class<?> target=tab==2?BrowserActivity.class:tab==4?PhotoActivity.class:MainActivity.class;
        if(tab==2||tab==4)a.stopService(new android.content.Intent(a,ProtectionService.class));
        a.startActivity(new android.content.Intent(a,target).putExtra("tab",tab).addFlags(android.content.Intent.FLAG_ACTIVITY_CLEAR_TOP|android.content.Intent.FLAG_ACTIVITY_SINGLE_TOP));
        if(!(a instanceof MainActivity))a.finish();
    }
    static void message(Context c,String s){new android.app.AlertDialog.Builder(c).setMessage(s).setPositiveButton("OK",null).show();}
    private static final class Icon extends View{
        private final Paint p=new Paint(Paint.ANTI_ALIAS_FLAG);private final int kind,color;
        Icon(Context c,int kind,int color){super(c);this.kind=kind;this.color=color;setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_NO);}
        @Override protected void onDraw(Canvas canvas){canvas.save();canvas.scale(getWidth()/24f,getHeight()/24f);p.setColor(color);p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(1.6f);p.setStrokeCap(Paint.Cap.ROUND);
            if(kind==0){Path s=new Path();s.moveTo(12,2);s.lineTo(21,6);s.lineTo(19,16);s.quadTo(16,21,12,23);s.quadTo(8,21,5,16);s.lineTo(3,6);s.close();canvas.drawPath(s,p);canvas.drawCircle(12,11,3,p);}
            if(kind==1){for(int y=5;y<=19;y+=7)canvas.drawLine(2,y,22,y,p);canvas.drawCircle(15,5,2.5f,p);canvas.drawCircle(8,12,2.5f,p);canvas.drawCircle(15,19,2.5f,p);}
            if(kind==2){canvas.drawRoundRect(2,3,22,20,2,2,p);canvas.drawLine(2,8,22,8,p);canvas.drawLine(7,5,8,5,p);canvas.drawLine(11,5,12,5,p);}
            if(kind==3){canvas.drawCircle(12,12,10,p);p.setStyle(Paint.Style.FILL);p.setTextSize(17);p.setTypeface(Typeface.DEFAULT_BOLD);p.setTextAlign(Paint.Align.CENTER);canvas.drawText("?",12,18,p);}
            if(kind==4){canvas.drawLine(12,2,12,16,p);canvas.drawLine(6,10,12,16,p);canvas.drawLine(18,10,12,16,p);canvas.drawLine(3,17,3,22,p);canvas.drawLine(3,22,21,22,p);canvas.drawLine(21,22,21,17,p);}canvas.restore();
        }
    }
}
