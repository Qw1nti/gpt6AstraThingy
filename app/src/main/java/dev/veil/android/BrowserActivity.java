package dev.veil.android;
import android.annotation.SuppressLint;
import android.app.*;
import android.graphics.*;
import android.net.Uri;
import android.os.*;
import android.view.*;
import android.webkit.*;
import android.widget.*;
import org.json.JSONArray;
import java.util.*;

public final class BrowserActivity extends Activity {
    private WebView web;
    private final ArrayList<WebView> tabs=new ArrayList<>();
    private FrameLayout viewport;
    private MaskView masks;
    private EditText address;
    private TextView status;
    private Prefs prefs;
    private final Handler main=new Handler(Looper.getMainLooper());
    private HandlerThread thread;
    private Handler worker;
    private Detector detector;
    private final MotionTracker tracker=new MotionTracker();
    private Bitmap browserFrame;
    private Canvas frameCanvas;
    private boolean active,busy,destroyed,failed;
    private int generation;
    private void nextScan(long started){
        if(active&&!destroyed&&!failed){main.removeCallbacks(scan);main.postDelayed(scan,Math.max(0,prefs.interval()-(SystemClock.elapsedRealtime()-started)));}
    }
    private final Runnable scan=new Runnable(){public void run(){
        if(!active||destroyed||failed||busy)return;
        if(!prefs.enabled()){masks.clear();tracker.clear();status.setText("AI detection is off");main.postDelayed(this,250);return;}
        if(web==null||web.getWidth()==0||web.getHeight()==0){main.postDelayed(this,32);return;}
        busy=true;int token=generation;long captured=SystemClock.elapsedRealtime();
        float scale=Math.min(1f,640f/Math.max(web.getWidth(),web.getHeight()));
        final int width=Math.max(1,Math.round(web.getWidth()*scale)),height=Math.max(1,Math.round(web.getHeight()*scale));
        try{
            if(browserFrame==null||browserFrame.getWidth()!=width||browserFrame.getHeight()!=height){
                if(browserFrame!=null)browserFrame.recycle();
                browserFrame=Bitmap.createBitmap(width,height,Bitmap.Config.ARGB_8888);frameCanvas=new Canvas(browserFrame);
            }
            frameCanvas.drawColor(Color.BLACK);int save=frameCanvas.save();frameCanvas.scale(scale,scale);web.draw(frameCanvas);frameCanvas.restoreToCount(save);
        }catch(RuntimeException e){busy=false;failed=true;masks.fillEntire();status.setText("Could not capture this page — reopen the browser");return;}
        Bitmap frame=browserFrame;
        worker.post(()->{try{
            if(detector==null)detector=new Detector(BrowserActivity.this);
            List<DetectionCore.Box> result=detector.detect(frame,prefs);Bitmap pixels=MaskView.pixelate(frame,prefs);
            long ms=SystemClock.elapsedRealtime()-captured;
            main.post(()->{busy=false;if(!destroyed&&active&&token==generation){
                tracker.update(result,width,height,captured);masks.update(tracker.snapshot(SystemClock.elapsedRealtime()),width,height,pixels);
                status.setText("AI active · "+result.size()+" regions · "+ms+" ms");
            }nextScan(captured);});
        }catch(Exception e){main.post(()->{busy=false;if(destroyed)return;failed=true;status.setText("Filtering failed — reopen the browser");masks.fillEntire();});}});
    }};
    @Override public void onCreate(Bundle saved){
        super.onCreate(saved);prefs=new Prefs(this);thread=new HandlerThread("Veil browser detector");thread.start();worker=new Handler(thread.getLooper());
        LinearLayout root=Ui.column(this);root.addView(Ui.navigation(this,2,n->Ui.openTab(this,n)));
        LinearLayout header=Ui.card(this);LinearLayout.LayoutParams hp=new LinearLayout.LayoutParams(-1,-2);hp.setMargins(Ui.dp(this,16),0,Ui.dp(this,16),Ui.dp(this,10));header.setLayoutParams(hp);
        header.addView(Ui.text(this,"Browser Settings",16,Ui.TEXT));
        header.addView(Ui.check(this,"Enable AI detection",prefs.enabled(),b->{prefs.bool("enabled",b);generation++;transitionMask();}));
        status=Ui.text(this,"Starting local detection…",12,Ui.MUTED);header.addView(status);root.addView(header);
        LinearLayout addressRow=new LinearLayout(this);addressRow.setGravity(Gravity.CENTER_VERTICAL);addressRow.setPadding(Ui.dp(this,16),0,Ui.dp(this,16),Ui.dp(this,8));
        address=new EditText(this);address.setSingleLine(true);address.setTextSize(13);address.setTextColor(Ui.TEXT);address.setHint("Search or enter URL");address.setPadding(Ui.dp(this,12),0,Ui.dp(this,8),0);address.setBackground(Ui.shape(this,Ui.CARD,Ui.LINE,8));
        address.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_VARIATION_URI);address.setImeOptions(android.view.inputmethod.EditorInfo.IME_ACTION_GO);
        address.setOnEditorActionListener((v,action,event)->{navigate(address.getText().toString());return true;});addressRow.addView(address,new LinearLayout.LayoutParams(0,Ui.dp(this,44),1));
        Button go=Ui.button(this,"Go",Ui.GREEN,Ui.BG,()->navigate(address.getText().toString()));LinearLayout.LayoutParams gp=new LinearLayout.LayoutParams(Ui.dp(this,55),Ui.dp(this,44));gp.leftMargin=Ui.dp(this,8);addressRow.addView(go,gp);root.addView(addressRow);
        LinearLayout tools=new LinearLayout(this);tools.setPadding(Ui.dp(this,16),0,Ui.dp(this,16),Ui.dp(this,8));
        String[] labels={"Back","Reload","Tabs","Bookmarks"};Runnable[] actions={()->{if(web.canGoBack())web.goBack();},()->web.reload(),this::tabMenu,this::bookmarks};
        for(int i=0;i<labels.length;i++){Button b=Ui.button(this,labels[i],Ui.CARD,Ui.MUTED,actions[i]);b.setTextSize(11);b.setLetterSpacing(0);tools.addView(b,new LinearLayout.LayoutParams(0,Ui.dp(this,40),1));}root.addView(tools);
        viewport=new FrameLayout(this);masks=new MaskView(this);masks.setClickable(false);root.addView(viewport,new LinearLayout.LayoutParams(-1,0,1));
        TextView caveat=Ui.text(this,"For video, use screen capture protection",10,Ui.MUTED);caveat.setGravity(Gravity.CENTER);root.addView(caveat);
        Ui.install(this,root);newTab();
    }
    @SuppressLint("SetJavaScriptEnabled")
    private WebView createWeb(){
        WebView view=new WebView(this);view.setBackgroundColor(Ui.BG);
        WebSettings s=view.getSettings();s.setJavaScriptEnabled(true);s.setDomStorageEnabled(true);s.setAllowFileAccess(false);s.setAllowContentAccess(false);s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);s.setSafeBrowsingEnabled(true);s.setMediaPlaybackRequiresUserGesture(true);s.setSupportMultipleWindows(false);CookieManager.getInstance().setAcceptThirdPartyCookies(view,false);
        view.addOnLayoutChangeListener((v,l,t,r,b,ol,ot,or,ob)->{if(v==web&&(r-l!=or-ol||b-t!=ob-ot)){generation++;transitionMask();}});
        view.setOnScrollChangeListener((v,x,y,oldX,oldY)->{if(v==web){
            generation++;tracker.clear();if(failed||prefs.invert())masks.fillEntire();else masks.scroll(oldX-x,oldY-y);
        }});
        view.setWebViewClient(new WebViewClient(){
            @Override public boolean shouldOverrideUrlLoading(WebView v,WebResourceRequest request){return !"https".equalsIgnoreCase(request.getUrl().getScheme());}
            @Override public void onPageStarted(WebView v,String url,Bitmap icon){if(v==web){generation++;transitionMask();address.setText(url.contains("veil.invalid")?"":url);}}
        });
        view.setWebChromeClient(new WebChromeClient(){@Override public void onPermissionRequest(PermissionRequest r){r.deny();}});
        view.setDownloadListener((url,agent,disposition,mime,length)->Ui.message(this,"Use Export to select a local photo and save a censored copy. Direct browser downloads are not enabled."));return view;
    }
    private void transitionMask(){tracker.clear();if(failed)masks.fillEntire();else masks.clear();}
    private void newTab(){
        if(tabs.size()>=4){Ui.message(this,"Four tabs are open. Close one before adding another.");return;}
        WebView next=createWeb();tabs.add(next);switchTab(next);
        next.loadDataWithBaseURL("https://veil.invalid/","<html><meta name='viewport' content='width=device-width,initial-scale=1'><body style='margin:0;background:#11000f;color:#ece9f0;font:14px sans-serif'><main style='padding:44px 20px;text-align:center'><div style='color:#ff0095;font-size:42px;font-weight:800;letter-spacing:3px'>VEIL</div><div style='color:#aaa2b1;font-size:12px;letter-spacing:2px'>FILTERED BROWSER</div><p style='margin-top:30px'>Enter an address above to start browsing.</p><p style='color:#aaa2b1;font-size:12px;line-height:1.6'>Detection runs locally on page images.<br>This is a regular session. Cookies persist.</p></main></body></html>","text/html","UTF-8",null);
    }
    private void switchTab(WebView next){if(web!=null)web.onPause();generation++;transitionMask();viewport.removeAllViews();web=next;viewport.addView(web,new FrameLayout.LayoutParams(-1,-1));viewport.addView(masks,new FrameLayout.LayoutParams(-1,-1));if(active)web.onResume();String url=web.getUrl();address.setText(url==null||url.contains("veil.invalid")?"":url);}
    private void tabMenu(){
        String[] labels=new String[tabs.size()];for(int i=0;i<labels.length;i++){String title=tabs.get(i).getTitle();labels[i]=(tabs.get(i)==web?"● ":"")+(title==null?"New tab":title);}
        new AlertDialog.Builder(this).setTitle("Open tabs ("+tabs.size()+"/4)").setItems(labels,(d,n)->switchTab(tabs.get(n)))
            .setPositiveButton("New tab",(d,n)->newTab()).setNeutralButton("Close current",(d,n)->{
                WebView old=web;tabs.remove(old);viewport.removeAllViews();web=null;old.stopLoading();old.destroy();if(tabs.isEmpty())newTab();else switchTab(tabs.get(tabs.size()-1));
            }).setNegativeButton("Done",null).show();
    }
    private void navigate(String raw){String value=raw.trim();if(value.isEmpty())return;
        if(!value.contains(".")||value.contains(" "))value="https://duckduckgo.com/?q="+Uri.encode(value);else if(!value.contains("://"))value="https://"+value;
        Uri uri=Uri.parse(value);if(!"https".equalsIgnoreCase(uri.getScheme())||uri.getHost()==null){Ui.message(this,"Enter an HTTPS website address.");return;}
        ((android.view.inputmethod.InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).hideSoftInputFromWindow(address.getWindowToken(),0);web.loadUrl(value);web.requestFocus();
    }
    private void bookmarks(){
        ArrayList<String> urls=new ArrayList<>();try{JSONArray a=new JSONArray(prefs.p.getString("bookmarks","[]"));for(int i=0;i<a.length();i++)urls.add(a.getString(i));}catch(Exception ignored){}
        String[] items=urls.toArray(new String[0]);new AlertDialog.Builder(this).setTitle("Bookmarks").setItems(items,(d,n)->navigate(items[n])).setPositiveButton("Save page",(d,n)->{
            String url=web.getUrl();if(url!=null&&url.startsWith("https://")&&!url.contains("veil.invalid")&&!urls.contains(url)){urls.add(url);prefs.p.edit().putString("bookmarks",new JSONArray(urls).toString()).apply();}
        }).setNeutralButton("Clear saved",(d,n)->prefs.p.edit().remove("bookmarks").apply()).setNegativeButton("Close",null).show();
    }
    @Override protected void onResume(){super.onResume();active=true;if(web!=null)web.onResume();main.removeCallbacks(scan);main.post(scan);}
    @Override protected void onPause(){active=false;generation++;tracker.clear();main.removeCallbacks(scan);if(web!=null)web.onPause();super.onPause();}
    @Override public void onBackPressed(){if(web!=null&&web.canGoBack())web.goBack();else super.onBackPressed();}
    @Override protected void onDestroy(){destroyed=true;active=false;generation++;main.removeCallbacks(scan);viewport.removeAllViews();for(WebView v:tabs){v.stopLoading();v.destroy();}tabs.clear();worker.post(()->{if(browserFrame!=null){browserFrame.recycle();browserFrame=null;}if(detector!=null)try{detector.close();}catch(Exception ignored){}thread.quitSafely();});super.onDestroy();}
}
