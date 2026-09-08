package dev.veil.android;

import android.app.*;
import android.content.*;
import android.content.pm.ServiceInfo;
import android.graphics.*;
import android.hardware.display.*;
import android.media.Image;
import android.media.ImageReader;
import android.media.projection.*;
import android.os.*;
import android.provider.Settings;
import android.view.WindowManager;
import java.util.List;

public final class ProtectionService extends Service {
    public static volatile boolean running;
    public static volatile String status="Protection is off";
    public static volatile long frames,lastMs;
    private final Handler main=new Handler(Looper.getMainLooper());
    private HandlerThread thread;
    private Handler worker;
    private Detector detector;
    private final CaptureBuffer captureBuffer=new CaptureBuffer();
    private MediaProjection projection;
    private VirtualDisplay display;
    private ImageReader reader;
    private OverlayController overlays;
    private Prefs prefs;
    private volatile boolean closed,visible=true;
    private volatile int generation;
    private long lastFrame,lastReceived;
    private int captureW,captureH;
    private final MediaProjection.Callback callback=new MediaProjection.Callback() {
        @Override public void onStop() { main.post(()->{ status="Protection stopped by Android"; stopSelf(); }); }
        @Override public void onCapturedContentResize(int w,int h) {
            if(!closed && w>0 && h>0) {
                generation++;
                main.post(()->overlays.clear());
                try { resize(w,h); } catch(Exception e) { fail("Screen resize failed",e); }
            }
        }
        @Override public void onCapturedContentVisibilityChanged(boolean isVisible) {
            visible=isVisible; generation++;
            if(!isVisible) main.post(()->{ overlays.clear(); status="Paused — selected app is hidden"; });
        }
    };
    private final Runnable watchdog=new Runnable() { public void run() {
        if(closed) return;
        // A static selected app may not produce new frames. Do not treat idle content as a failed capture.
        if(visible && lastReceived>0 && SystemClock.elapsedRealtime()-lastReceived>6000)
            status="Waiting for screen changes";
        worker.postDelayed(this,2000);
    }};
    @Override public void onCreate() {
        super.onCreate(); prefs=new Prefs(this); overlays=new OverlayController(this);
        thread=new HandlerThread("Veil inference"); thread.start(); worker=new Handler(thread.getLooper());
        getSystemService(NotificationManager.class).createNotificationChannel(new NotificationChannel("protection","Screen protection",NotificationManager.IMPORTANCE_LOW));
    }
    @Override public int onStartCommand(Intent intent,int flags,int id) {
        if(intent!=null && "STOP".equals(intent.getAction())) { stopSelf(); return START_NOT_STICKY; }
        if(running || closed) return START_NOT_STICKY;
        Intent data=intent==null?null:intent.getParcelableExtra("capture",Intent.class);
        if(data==null || !Settings.canDrawOverlays(this)) { status="Screen capture or overlay permission missing"; stopSelf(); return START_NOT_STICKY; }
        try {
            startForeground(101,notification("Starting local detector"),ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION);
            running=true; frames=0; lastMs=0; status="Loading detector…";
            projection=getSystemService(MediaProjectionManager.class).getMediaProjection(intent.getIntExtra("code",Activity.RESULT_CANCELED),data);
            projection.registerCallback(callback,worker);
            Rect screen=getSystemService(WindowManager.class).getMaximumWindowMetrics().getBounds();
            worker.post(()->{
                if(closed) return;
                try {
                    detector=new Detector(this);
                    if(closed) return;
                    resize(screen.width(),screen.height());
                    display=projection.createVirtualDisplay("Veil local analysis",captureW,captureH,
                        getResources().getConfiguration().densityDpi,DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                        reader.getSurface(),null,worker);
                    lastReceived=SystemClock.elapsedRealtime();
                    status="Protection active — select one full-screen app";
                    main.post(()->{ if(!closed) getSystemService(NotificationManager.class).notify(101,notification("Local screen filtering is active")); });
                    worker.postDelayed(watchdog,2000);
                } catch(Exception e) { fail("Could not start protection",e); }
            });
        } catch(Exception e) { fail("Capture permission expired. Start again",e); }
        return START_NOT_STICKY;
    }
    private Notification notification(String message) {
        PendingIntent open=PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        PendingIntent stop=PendingIntent.getService(this,1,new Intent(this,ProtectionService.class).setAction("STOP"),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        return new Notification.Builder(this,"protection").setSmallIcon(dev.veil.android.R.drawable.ic_shield)
            .setContentTitle("Veil protection").setContentText(message).setContentIntent(open).setOngoing(true)
            .addAction(new Notification.Action.Builder(null,"Stop protection",stop).build()).build();
    }
    /** Resize the existing virtual display, never create a second one with the same token. */
    private void resize(int w,int h) {
        float scale=Math.min(1f,640f/Math.max(w,h));
        int nextW=Math.max(1,Math.round(w*scale)),nextH=Math.max(1,Math.round(h*scale));
        if(reader!=null && captureW==nextW && captureH==nextH) return;
        ImageReader next=ImageReader.newInstance(nextW,nextH,PixelFormat.RGBA_8888,2);
        ImageReader old=reader; captureW=nextW; captureH=nextH;
        reader=next; next.setOnImageAvailableListener(this::frame,worker);
        if(display!=null) {
            display.setSurface(null);
            display.resize(captureW,captureH,getResources().getConfiguration().densityDpi);
            display.setSurface(next.getSurface());
        }
        if(old!=null) { old.setOnImageAvailableListener(null,null); old.close(); }
    }
    private void frame(ImageReader source) {
        if(closed || source!=reader) return;
        Bitmap bitmap;
        long captured;
        int token,width,height;
        try {
            // Release the ImageReader buffer before inference so capture can keep producing frames.
            try(Image image=source.acquireLatestImage()) {
                if(image==null) return;
                captured=SystemClock.elapsedRealtime(); lastReceived=captured;
                if(!visible || detector==null || captured-lastFrame<prefs.interval()) return;
                if(!prefs.enabled()) { main.post(()->overlays.clear()); return; }
                lastFrame=captured; token=generation;
                width=image.getWidth();height=image.getHeight();
                bitmap=captureBuffer.copy(image);
            }
            List<DetectionCore.Box> boxes=detector.detect(bitmap,prefs);
            Bitmap pixels=MaskView.pixelate(bitmap,prefs);
            lastMs=SystemClock.elapsedRealtime()-captured; frames++;
            main.post(()->{
                if(closed || !visible || token!=generation) return;
                if(!Settings.canDrawOverlays(this)) { fail("Overlay permission was removed",null); return; }
                try { overlays.show(boxes,width,height,pixels,captured); status="Active · "+boxes.size()+" detections"+(boxes.size()>24?" · grouped":"")+(prefs.style()==3?" · outline only":prefs.invert()?" · inverted":""); }
                catch(RuntimeException e) { fail("Could not display censor boxes",e); }
            });
        } catch(Exception e) { if(!closed) fail("Screen detection failed",e); }
    }
    private void fail(String message,Exception error) {
        main.post(()->{ if(closed) return;
            status=message+(error==null?"":" ("+error.getClass().getSimpleName()+")");
            android.widget.Toast.makeText(this,status,android.widget.Toast.LENGTH_LONG).show(); stopSelf();
        });
    }
    @Override public void onDestroy() {
        closed=true; running=false; generation++;
        if(status.startsWith("Active")||status.startsWith("Protection active")||status.startsWith("Loading")||status.startsWith("Paused")||status.startsWith("Waiting")) status="Protection is off";
        if(overlays!=null) overlays.clear();
        if(worker!=null) worker.post(()->{
            worker.removeCallbacks(watchdog);
            if(display!=null) { display.release(); display=null; }
            if(reader!=null) { reader.setOnImageAvailableListener(null,null); reader.close(); reader=null; }
            if(projection!=null) { projection.unregisterCallback(callback); projection.stop(); projection=null; }
            if(detector!=null) { try { detector.close(); } catch(Exception ignored) {} detector=null; }
            captureBuffer.close();
            thread.quitSafely();
        });
        stopForeground(STOP_FOREGROUND_REMOVE); super.onDestroy();
    }
    @Override public IBinder onBind(Intent intent) { return null; }
}
