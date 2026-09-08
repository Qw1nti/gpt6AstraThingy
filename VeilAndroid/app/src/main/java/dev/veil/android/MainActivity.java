package dev.veil.android;

import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.media.projection.MediaProjectionManager;
import android.net.Uri;
import android.os.*;
import android.provider.Settings;
import android.view.*;
import android.widget.*;

public final class MainActivity extends Activity {
    private static final int CAPTURE=10,NOTIFICATIONS=11;
    private Prefs prefs;
    private TextView status,stats;
    private Button start;
    private int selected;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final Runnable refresh=new Runnable(){public void run(){
        if(status!=null)status.setText(ProtectionService.status);
        if(stats!=null)stats.setText(ProtectionService.frames+" frames checked   ·   "+ProtectionService.lastMs+" ms last scan");
        if(start!=null)start.setText(ProtectionService.running?"Stop Protection":"Start Protection");
        handler.postDelayed(this,800);
    }};
    @Override public void onCreate(Bundle saved){super.onCreate(saved);prefs=new Prefs(this);showTab(saved==null?getIntent().getIntExtra("tab",0):saved.getInt("tab",0));}
    @Override protected void onNewIntent(Intent intent){super.onNewIntent(intent);setIntent(intent);showTab(intent.getIntExtra("tab",0));}
    @Override protected void onSaveInstanceState(Bundle state){state.putInt("tab",selected);super.onSaveInstanceState(state);}
    private void showTab(int tab){
        if(tab==2||tab==4){stopService(new Intent(this,ProtectionService.class));startActivity(new Intent(this,tab==2?BrowserActivity.class:PhotoActivity.class));return;}
        selected=tab==1||tab==3?tab:0;status=null;stats=null;start=null;
        LinearLayout root=Ui.column(this);root.addView(Ui.navigation(this,selected,this::showTab));
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(false);
        LinearLayout content=Ui.column(this);int p=Ui.dp(this,16);content.setPadding(p,0,p,p);scroll.addView(content);
        root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
        if(selected==0)home(content);else if(selected==1)settings(content);else help(content);
        Ui.install(this,root);
    }
    private LinearLayout section(LinearLayout parent,String title,String description){
        LinearLayout c=Ui.card(this);c.addView(Ui.text(this,title,16,Ui.TEXT));
        if(description!=null)c.addView(Ui.text(this,description,12,Ui.MUTED));parent.addView(c);return c;
    }
    private void home(LinearLayout content){
        LinearLayout capture=section(content,"Screen Capture Protection","Start or stop the screen capture service.");
        start=Ui.button(this,ProtectionService.running?"Stop Protection":"Start Protection",Ui.GREEN,Ui.BG,()->{
            if(ProtectionService.running)stopService(new Intent(this,ProtectionService.class));else begin();
        });capture.addView(start);
        LinearLayout ai=section(content,"AI Censoring","Detect and censor the categories you choose.");
        ai.addView(Ui.check(this,"Enable AI detection",prefs.enabled(),b->{prefs.bool("enabled",b);if(!b)stopService(new Intent(this,ProtectionService.class));}));
        ai.addView(Ui.outline(this,"Censor style: "+prefs.styleName(),()->showTab(1)));
        ai.addView(Ui.text(this,"Quick toggles",13,Ui.TEXT));
        LinearLayout row=new LinearLayout(this);
        row.addView(Ui.check(this,"Invert censor",prefs.invert(),b->prefs.bool("invert",b)),new LinearLayout.LayoutParams(0,-2,1));
        row.addView(Ui.check(this,"Show labels",prefs.labels(),b->prefs.bool("labels",b)),new LinearLayout.LayoutParams(0,-2,1));ai.addView(row);
        slider(ai,"Censor coverage","padding",0,70,18,"%");
        LinearLayout performance=section(content,"Performance","Choose a preset to match your device.");
        choice(performance,"preset",new String[]{"Low","Medium","High","Ultra"},1);
        LinearLayout session=section(content,"Session",null);
        status=Ui.text(this,ProtectionService.status,13,Ui.MUTED);session.addView(status);
        stats=Ui.text(this,"0 frames checked",12,Ui.MUTED);session.addView(stats);
        session.addView(Ui.text(this,"Use one-app capture. Detection can be delayed or miss content.",12,Ui.MUTED));
        TextView footer=Ui.text(this,"Veil 0.2  ·  On-device filtering",11,Ui.MUTED);footer.setGravity(Gravity.CENTER);content.addView(footer);
    }
    private void settings(LinearLayout content){
        LinearLayout effects=section(content,"Effects and packs","Preview your censor style or apply a saved look.");
        effects.addView(Ui.button(this,"Censor Preview",this::preview));effects.addView(Ui.button(this,"Style Presets",this::presets));
        LinearLayout language=section(content,"Language",null);language.addView(Ui.text(this,"English",18,Ui.TEXT));
        LinearLayout categories=section(content,"Detection Categories",null);
        String[] names={"Genitals (F)","Genitals (M)","Breasts (Female)","Buttocks","Anus","Genitals (Covered)","Breasts (Covered)","Buttocks (Covered)","Anus (Covered)","All Faces","Chest (Male)","Belly/Stomach","Feet","Armpits"};
        int[] bits={1<<4,1<<14,1<<3,1<<2,1<<6,1,1<<16,1<<17,1<<15,(1<<1)|(1<<12),1<<5,(1<<8)|(1<<13),(1<<7)|(1<<9),(1<<10)|(1<<11)};
        for(int i=0;i<names.length;i+=2){LinearLayout row=new LinearLayout(this);
            for(int j=i;j<Math.min(i+2,names.length);j++){final int mask=bits[j];
                row.addView(Ui.check(this,names[j],(prefs.mask()&mask)!=0,on->prefs.put("mask",on?prefs.mask()|mask:prefs.mask()&~mask)),new LinearLayout.LayoutParams(0,-2,1));
            }categories.addView(row);
        }
        LinearLayout style=section(content,"Censor Style",null);choice(style,"style",Prefs.STYLES,0);
        style.addView(Ui.text(this,"Box outline marks detections but does not hide their contents.",12,Ui.MUTED));
        style.addView(Ui.text(this,"Censor color",13,Ui.TEXT));
        choice(style,"color",new String[]{"Black","Hot pink","Purple","Lime"},0);
        style.addView(Ui.check(this,"Invert censoring",prefs.invert(),b->prefs.bool("invert",b)));
        style.addView(Ui.text(this,"Invert covers everything outside detected regions. Screen overlays can block touches; Stop stays in the notification.",12,Ui.MUTED));
        style.addView(Ui.check(this,"Show text on censor",prefs.labels(),b->prefs.bool("labels",b)));
        EditText label=new EditText(this);label.setSingleLine(true);label.setText(prefs.label());label.setHint("Censor text");label.setTextSize(15);
        label.setFilters(new android.text.InputFilter[]{new android.text.InputFilter.LengthFilter(32)});
        label.addTextChangedListener(new android.text.TextWatcher(){
            public void beforeTextChanged(CharSequence s,int start,int count,int after){}
            public void onTextChanged(CharSequence s,int start,int before,int count){prefs.p.edit().putString("label",s.toString()).apply();}
            public void afterTextChanged(android.text.Editable s){}
        });style.addView(label);
        LinearLayout detection=section(content,"Detection Settings",null);
        slider(detection,"Confidence threshold","confidence",20,90,45,"%");
        slider(detection,"Extra coverage","padding",0,70,18,"%");
        slider(detection,"Screen vertical adjustment","offset",-120,120,0," dp");
        detection.addView(Ui.text(this,"Lower confidence catches more with more false positives. Vertical adjustment is for full-screen app alignment.",12,Ui.MUTED));
    }
    private void help(LinearLayout content){
        LinearLayout permission=section(content,"Permissions & battery","Appear-on-top permission lets Veil draw censor regions. Android asks for screen capture approval for each session.");
        permission.addView(Ui.button(this,"Overlay Settings",()->startActivity(new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,Uri.parse("package:"+getPackageName())))));
        permission.addView(Ui.button(this,"Battery Settings",()->startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,Uri.parse("package:"+getPackageName())))));
        LinearLayout guide=section(content,"Quick guide","1. Tap Start Protection on Home.\n2. Choose one app in Android’s capture dialog.\n3. Keep the app full screen.\n4. Pick your categories and censor style in Settings.");
        guide.addView(Ui.text(this,"Censor regions absorb touches. Scroll outside them. Box outline is a preview style; it leaves content visible. Invert hides the surrounding screen.",13,Ui.MUTED));
        LinearLayout tips=section(content,"If something looks wrong","Stop protection and start a new capture session. For offset boxes, try the vertical adjustment slider. Split screen and protected video are unsupported.");
        tips.addView(Ui.text(this,"The built-in browser filters page images. Hardware video and WebGL may remain unfiltered. No filter can guarantee every region is caught.",13,Ui.MUTED));
        LinearLayout privacy=section(content,"Privacy","Detection stays on your phone. No accounts, telemetry, uploads, or automatic recording. Browser websites receive normal browsing traffic and can store cookies.");
        privacy.addView(Ui.text(this,"Veil is an independent experimental implementation. On-device behavior and APK compilation remain unverified in this source build.",12,Ui.MUTED));
    }
    private void presets(){new AlertDialog.Builder(this).setTitle("Style presets").setItems(new String[]{"Classic black","Pink labels","Purple pattern","Detection outline"},(d,n)->{
        prefs.put("style",new int[]{0,2,1,3}[n]);prefs.put("color",new int[]{0,1,2,3}[n]);prefs.bool("labels",n==1);showTab(1);
    }).setNegativeButton("Cancel",null).show();}
    private void preview(){
        MaskView demo=new MaskView(this);demo.update(java.util.List.of(new DetectionCore.Box(25,20,75,80,.95f,3)),100,100);
        demo.setBackgroundColor(0xFF747080);
        new AlertDialog.Builder(this).setTitle("Style preview · simulated region").setView(demo,16,16,16,16).setPositiveButton("Done",null).show().getWindow().setLayout(Ui.dp(this,320),Ui.dp(this,290));
    }
    private void begin(){
        if(prefs.mask()==0){Ui.message(this,"Choose at least one detection category first.");return;}
        if(!prefs.enabled()){prefs.bool("enabled",true);showTab(0);}
        if(!Settings.canDrawOverlays(this)){
            new AlertDialog.Builder(this).setTitle("Allow censor boxes").setMessage("Enable ‘Appear on top’ for Veil, then return and tap Start Protection again.")
                .setPositiveButton("Open settings",(d,w)->startActivity(new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,Uri.parse("package:"+getPackageName())))).setNegativeButton("Cancel",null).show();return;
        }
        if(checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED&&!prefs.p.getBoolean("notificationAsked",false)){
            prefs.p.edit().putBoolean("notificationAsked",true).apply();requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},NOTIFICATIONS);return;
        }
        new AlertDialog.Builder(this).setTitle("Choose one app").setMessage("Select a single app in Android’s next dialog and keep it full screen. Entire-screen capture can recapture the censor boxes and is unsupported.\n\nStop anytime from Veil, the notification, or Android’s capture indicator.")
            .setPositiveButton("Continue",(d,w)->startActivityForResult(getSystemService(MediaProjectionManager.class).createScreenCaptureIntent(),CAPTURE)).setNegativeButton("Cancel",null).show();
    }
    @Override public void onRequestPermissionsResult(int req,String[] permissions,int[] results){super.onRequestPermissionsResult(req,permissions,results);if(req==NOTIFICATIONS)begin();}
    @Override protected void onActivityResult(int req,int result,Intent data){super.onActivityResult(req,result,data);if(req==CAPTURE&&result==RESULT_OK&&data!=null){try{startForegroundService(new Intent(this,ProtectionService.class).putExtra("code",result).putExtra("capture",data));}catch(RuntimeException e){Ui.message(this,"Could not start protection: "+e.getClass().getSimpleName());}}}
    private void choice(LinearLayout parent,String key,String[] labels,int def){
        Spinner s=new Spinner(this);s.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,labels));s.setSelection(Math.max(0,Math.min(labels.length-1,prefs.p.getInt(key,def))));s.setMinimumHeight(Ui.dp(this,48));
        s.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){public void onItemSelected(AdapterView<?> p,View v,int n,long id){prefs.put(key,n);}public void onNothingSelected(AdapterView<?> p){}});parent.addView(s);
    }
    private void slider(LinearLayout parent,String name,String key,int min,int max,int def,String suffix){
        TextView label=Ui.text(this,name+": "+prefs.p.getInt(key,def)+suffix,13,Ui.MUTED);parent.addView(label);
        SeekBar bar=new SeekBar(this);bar.setProgressTintList(android.content.res.ColorStateList.valueOf(Ui.PINK));bar.setThumbTintList(android.content.res.ColorStateList.valueOf(Ui.PINK));bar.setMax(max-min);bar.setProgress(prefs.p.getInt(key,def)-min);bar.setMinimumHeight(Ui.dp(this,42));
        bar.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){public void onProgressChanged(SeekBar s,int n,boolean user){if(user){prefs.put(key,n+min);label.setText(name+": "+(n+min)+suffix);}}public void onStartTrackingTouch(SeekBar s){}public void onStopTrackingTouch(SeekBar s){}});parent.addView(bar);
    }
    @Override protected void onResume(){super.onResume();handler.removeCallbacks(refresh);handler.post(refresh);}
    @Override protected void onPause(){handler.removeCallbacks(refresh);super.onPause();}
}
