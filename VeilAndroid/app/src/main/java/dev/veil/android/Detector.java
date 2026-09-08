package dev.veil.android;

import ai.onnxruntime.*;
import android.content.Context;
import android.graphics.*;
import java.io.*;
import java.nio.FloatBuffer;
import java.util.*;

/** Confined to one worker thread. No file/network operations on captured frames. */
final class Detector implements AutoCloseable {
    private final OrtEnvironment env=OrtEnvironment.getEnvironment();
    private final OrtSession session;
    private final String input;
    private final Bitmap square=Bitmap.createBitmap(320,320,Bitmap.Config.ARGB_8888);
    private final Canvas canvas=new Canvas(square);
    private final Paint sampling=new Paint(Paint.FILTER_BITMAP_FLAG);
    private final int[] pixels=new int[320*320];
    private final float[] tensor=new float[3*320*320];

    Detector(Context c) throws Exception {
        byte[] bytes;
        try(InputStream in=c.getAssets().open("320n.onnx")) { bytes=in.readAllBytes(); }
        try(OrtSession.SessionOptions options=new OrtSession.SessionOptions()) {
            options.setIntraOpNumThreads(2);
            options.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT);
            session=env.createSession(bytes,options);
        }
        input=session.getInputNames().iterator().next();
        TensorInfo info=(TensorInfo)session.getInputInfo().get(input).getInfo();
        if(!Arrays.equals(info.getShape(),new long[]{1,3,320,320})) {
            session.close(); throw new IllegalArgumentException("Unexpected detector input dimensions");
        }
    }
    List<DetectionCore.Box> detect(Bitmap source, Prefs prefs) throws Exception {
        // Square pad on right/bottom, black RGB, CHW float32 [0,1].
        canvas.drawColor(Color.BLACK);
        float scale=320f/Math.max(source.getWidth(),source.getHeight());
        canvas.drawBitmap(source,null,new RectF(0,0,source.getWidth()*scale,source.getHeight()*scale),sampling);
        square.getPixels(pixels,0,320,0,0,320,320);
        for(int i=0;i<pixels.length;i++) {
            tensor[i]=((pixels[i]>>16)&255)/255f;
            tensor[pixels.length+i]=((pixels[i]>>8)&255)/255f;
            tensor[2*pixels.length+i]=(pixels[i]&255)/255f;
        }
        try(OnnxTensor value=OnnxTensor.createTensor(env,FloatBuffer.wrap(tensor),new long[]{1,3,320,320});
            OrtSession.Result result=session.run(Collections.singletonMap(input,value))) {
            Object raw=result.get(0).getValue();
            if(!(raw instanceof float[][][])) throw new IllegalArgumentException("Unexpected detector output type");
            float[][][] batch=(float[][][])raw;
            if(batch.length!=1) throw new IllegalArgumentException("Unexpected detector batch size");
            List<DetectionCore.Box> boxes=DetectionCore.decode(batch[0],source.getWidth(),source.getHeight(),prefs.confidence(),prefs.mask());
            List<DetectionCore.Box> padded=new ArrayList<>();
            for(DetectionCore.Box box:boxes) padded.add(box.expand(prefs.padding(),source.getWidth(),source.getHeight()));
            return padded;
        }
    }
    public void close() throws OrtException { square.recycle(); session.close(); }
}
