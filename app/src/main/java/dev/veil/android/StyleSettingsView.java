package dev.veil.android;

import android.content.Context;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.Typeface;
import android.view.*;
import android.widget.*;

/** Settings-only controls; all preference keys and mask rendering semantics stay compatible. */
final class StyleSettingsView extends LinearLayout {
    private final Prefs prefs;
    private final Runnable chooseImage;
    private final StylePreviewView preview;
    private final TextView selectedName;
    private final LinearLayout options;
    private final Button[] styles=new Button[6];
    private static final String[] NAMES={"Solid","Pattern","Labeled","Outline","Custom image","Pixelated"};
    StyleSettingsView(Context context,Runnable chooseImage,Runnable presets){
        super(context);setOrientation(VERTICAL);prefs=new Prefs(context);this.chooseImage=chooseImage;
        LinearLayout card=Ui.card(context);addView(card);
        TextView title=Ui.text(context,"Censor style",20,Ui.TEXT);title.setTypeface(Typeface.DEFAULT_BOLD);card.addView(title);
        card.addView(Ui.text(context,"Choose your look. Make it yours.",14,Ui.MUTED));
        Ui.gap(card,12);
        preview=new StylePreviewView(context);preview.setTag("style-preview");
        card.addView(preview,new LayoutParams(-1,Ui.dp(context,156)));
        LinearLayout caption=new LinearLayout(context);caption.setGravity(Gravity.CENTER_VERTICAL);
        selectedName=Ui.text(context,"",13,Ui.GREEN);caption.addView(selectedName,new LayoutParams(0,-2,1));
        TextView simulated=Ui.text(context,"SIMULATED PREVIEW",10,Ui.MUTED);simulated.setLetterSpacing(.06f);caption.addView(simulated);card.addView(caption);
        Ui.gap(card,8);
        for(int row=0;row<3;row++){
            LinearLayout choices=new LinearLayout(context);
            for(int col=0;col<2;col++){
                int index=row*2+col;
                Button b=Ui.button(context,NAMES[index],()->{prefs.put("style",index);refresh();});b.setTag("style-"+index);b.setTextSize(14);b.setLetterSpacing(0);
                LayoutParams lp=new LayoutParams(0,-2,1);lp.topMargin=Ui.dp(context,6);if(col==0)lp.rightMargin=Ui.dp(context,8);
                choices.addView(b,lp);styles[index]=b;
            }card.addView(choices);
        }
        options=Ui.column(context);options.setTag("style-options");Ui.gap(card,12);card.addView(options);
        card.addView(Ui.outline(context,"Style presets",presets));

        LinearLayout coverage=Ui.card(context);addView(coverage);
        coverage.addView(Ui.text(context,"Censor coverage",18,Ui.TEXT));
        coverage.addView(Ui.text(context,"Smaller  ←  Detected size  →  Larger",13,Ui.MUTED));
        TextView sizeHint=Ui.text(context,"",13,Ui.MUTED);
        TextView value=Ui.text(context,"",18,Ui.GREEN);value.setGravity(Gravity.CENTER);value.setTag("coverage-value");coverage.addView(value);
        SeekBar bar=new SeekBar(context);bar.setTag("coverage-slider");bar.setContentDescription("Censor coverage");bar.setMax(110);bar.setProgress(prefs.p.getInt("padding",18)+40);tint(bar);coverage.addView(bar,new LayoutParams(-1,Ui.dp(context,48)));
        Runnable update=()->{int n=prefs.p.getInt("padding",18);value.setText((n>0?"+":"")+n+"%");sizeHint.setText(n==0?"Uses the detected box size.":"Box width and height: "+(100+2*n)+"% of detected size, before screen clipping.");preview.refresh();};
        bar.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){
            public void onProgressChanged(SeekBar s,int n,boolean user){prefs.put("padding",n-40);update.run();}
            public void onStartTrackingTouch(SeekBar s){}public void onStopTrackingTouch(SeekBar s){}
        });
        LinearLayout precise=new LinearLayout(context);
        Button minus=Ui.outline(context,"−",()->bar.setProgress(Math.max(0,bar.getProgress()-1)));minus.setContentDescription("Decrease coverage by one percent");minus.setTag("coverage-minus");
        Button reset=Ui.outline(context,"Reset to 0%",()->bar.setProgress(40));reset.setTag("coverage-reset");
        Button plus=Ui.outline(context,"+",()->bar.setProgress(Math.min(110,bar.getProgress()+1)));plus.setContentDescription("Increase coverage by one percent");plus.setTag("coverage-plus");
        precise.addView(minus,new LayoutParams(Ui.dp(context,48),-2));LayoutParams middle=new LayoutParams(0,-2,1);middle.setMargins(Ui.dp(context,8),0,Ui.dp(context,8),0);precise.addView(reset,middle);precise.addView(plus,new LayoutParams(Ui.dp(context,48),-2));coverage.addView(precise);
        coverage.addView(sizeHint);coverage.addView(Ui.text(context,"Shrinking can leave parts of a detected region visible.",12,Ui.MUTED));
        refresh();update.run();
    }
    void refresh(){
        int current=prefs.style();selectedName.setText(Prefs.STYLES[current]);
        for(int i=0;i<styles.length;i++){
            boolean active=i==current;Button b=styles[i];b.setSelected(active);b.setText((active?"✓  ":"")+NAMES[i]);
            b.setTextColor(active?Ui.BG:Ui.TEXT);b.setBackground(Ui.shape(getContext(),active?Ui.PINK:0xFF231D2E,active?Ui.PINK:Ui.LINE,10));
            b.setContentDescription(NAMES[i]+(active?", selected":""));
        }
        options.removeAllViews();Context c=getContext();
        if(current<=3)swatches(options,current==3?"Outline color":"Censor color","color",new String[]{"Black","Pink","Purple","Lime"},new int[]{Color.BLACK,Ui.PINK,0xFFB18AF0,Ui.GREEN});
        if(current==3)options.addView(Ui.text(c,"Outline only. The contents stay visible.",14,Ui.GREEN));
        if(current==4){
            android.graphics.Bitmap image=CustomMaskImage.load(c);
            if(image!=null){ImageView thumb=new ImageView(c);thumb.setImageBitmap(image);thumb.setScaleType(ImageView.ScaleType.CENTER_INSIDE);thumb.setContentDescription("Your custom censor image");thumb.setBackground(Ui.shape(c,Color.BLACK,Ui.LINE,8));options.addView(thumb,new LayoutParams(-1,Ui.dp(c,76)));}
            Button pick=Ui.button(c,image==null?"Choose an image":"Replace image",chooseImage);pick.setTag("custom-image-picker");options.addView(pick);
            if(image!=null){Button remove=Ui.outline(c,"Remove image",()->{CustomMaskImage.remove(c);refresh();});options.addView(remove);}
            options.addView(Ui.text(c,image==null?"Pick a photo or PNG. Until then, regions use black.":"Saved on your phone. Cropped to fill each region.",13,Ui.MUTED));
        }
        if(current==5){
            TextView blocks=Ui.text(c,"Pixel block size: "+prefs.pixelSize(),14,Ui.TEXT);options.addView(blocks);
            SeekBar bar=new SeekBar(c);bar.setTag("pixel-size");bar.setContentDescription("Pixel block size");bar.setMax(56);bar.setProgress(prefs.pixelSize()-8);tint(bar);options.addView(bar,new LayoutParams(-1,Ui.dp(c,48)));
            bar.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){public void onProgressChanged(SeekBar s,int n,boolean user){if(user){prefs.put("pixelSize",n+8);blocks.setText("Pixel block size: "+(n+8));preview.refresh();}}public void onStartTrackingTouch(SeekBar s){}public void onStopTrackingTouch(SeekBar s){}});
            swatches(options,"Border color","borderColor",new String[]{"Pink","Lime","White","Purple"},new int[]{Ui.PINK,Ui.GREEN,Color.WHITE,0xFFB18AF0});
        }
        options.addView(Ui.check(c,"Invert censoring",prefs.invert(),value->{prefs.bool("invert",value);preview.refresh();}));
        options.addView(Ui.text(c,"Invert covers everything outside detected regions.",12,Ui.MUTED));
        if(current!=3){
            LinearLayout textOptions=Ui.column(c);textOptions.setTag("label-options");
            if(current!=2)options.addView(Ui.check(c,"Show text",prefs.labels(),value->{prefs.bool("labels",value);textOptions.setVisibility(value?VISIBLE:GONE);preview.refresh();}));
            textOptions.addView(Ui.text(c,"Censor text",13,Ui.MUTED));
            EditText text=new EditText(c);text.setTag("censor-text");text.setSingleLine(true);text.setTextColor(Ui.TEXT);text.setTextSize(16);text.setHint("CENSORED");text.setText(prefs.label());text.setContentDescription("Censor text");text.setFilters(new android.text.InputFilter[]{new android.text.InputFilter.LengthFilter(32)});
            text.addTextChangedListener(new android.text.TextWatcher(){public void beforeTextChanged(CharSequence s,int start,int count,int after){}public void onTextChanged(CharSequence s,int start,int before,int count){prefs.p.edit().putString("label",s.toString()).apply();preview.refresh();}public void afterTextChanged(android.text.Editable e){}});
            textOptions.addView(text);textOptions.setVisibility(current==2||prefs.labels()?VISIBLE:GONE);options.addView(textOptions);
        }
        preview.refresh();
    }
    private void swatches(LinearLayout parent,String title,String key,String[] names,int[] colors){
        parent.addView(Ui.text(getContext(),title,14,Ui.TEXT));
        Button[] buttons=new Button[names.length];
        Runnable restyle=()->{int selected=prefs.p.getInt(key,0);for(int i=0;i<buttons.length;i++){Button b=buttons[i];if(b==null)continue;b.setText((i==selected?"✓ ":"")+names[i]);b.setSelected(i==selected);b.setBackground(Ui.shape(getContext(),colors[i],i==selected?Ui.TEXT:Ui.LINE,9));b.setTextColor(colors[i]==Color.BLACK?Color.WHITE:Ui.BG);}};
        for(int row=0;row<2;row++){
            LinearLayout line=new LinearLayout(getContext());
            for(int col=0;col<2;col++){int index=row*2+col;Button b=Ui.button(getContext(),names[index],()->{prefs.put(key,index);restyle.run();preview.refresh();});b.setTag(key+"-"+index);b.setTextSize(14);b.setLetterSpacing(0);LayoutParams lp=new LayoutParams(0,-2,1);lp.topMargin=Ui.dp(getContext(),6);if(col==0)lp.rightMargin=Ui.dp(getContext(),8);line.addView(b,lp);buttons[index]=b;}
            parent.addView(line);
        }restyle.run();
    }
    private void tint(SeekBar bar){bar.setProgressTintList(ColorStateList.valueOf(Ui.PINK));bar.setThumbTintList(ColorStateList.valueOf(Ui.PINK));}
}
