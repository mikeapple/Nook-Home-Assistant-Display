package com.mikeapple.myapplication;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.WindowManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.view.KeyEvent;
import org.json.JSONObject;
import org.json.JSONArray;
import java.util.Iterator;
import java.util.HashMap;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import android.util.Log;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileWriter;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.URL;
import java.io.FileInputStream;
import java.io.OutputStream;

// read log adb shell run-as com.mikeapple.myapplication cat files/refresh_trace.log
public class MainActivity extends Activity {

    private static final String TAG = "EnergyDashboard";
    private static final String LOG_FILE_NAME = "refresh_trace.log";
    private static final long LOG_FILE_MAX_BYTES = 1024 * 1024; // 1 MB
    private WebView webView;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private boolean refreshScheduled = false;
    private ServerSocket logServerSocket;

    // Toggle between JavaScript auto-refresh and Java injection
    // true = JavaScript handles updates (may cause e-ink flashing)
    // false = Java injects values via webView.loadUrl (gentler on e-ink)
    private static final boolean USE_JS_REFRESH = false;

    private static final long REFRESH_INTERVAL = 30000; // 30 seconds
    private static final long GROUP_DELAY = 5000; // 5 seconds between groups

    // Entity groups for staggered refresh (prevents e-ink flashing)
    private static final HashMap<Integer, String[]> ENTITY_GROUPS = new HashMap<Integer, String[]>() {{
        put(1, new String[]{"sensor.solarsynkv3_2212102484_pv_etoday", "sensor.solarsynkv3_2212102484_pv_pac"});
        put(2, new String[]{"sensor.solarsynkv3_2212102484_load_total_power", "sensor.solarsynkv3_2212102484_load_daily_used"});
        put(3, new String[]{"sensor.solarsynkv3_2212102484_battery_soc", "sensor.solarsynkv3_2212102484_battery_power", "sensor.solarsynkv3_2212102484_battery_etoday_charge", "sensor.solarsynkv3_2212102484_battery_etoday_discharge"});
        put(4, new String[]{"sensor.solarsynkv3_2212102484_grid_etoday_from", "sensor.solarsynkv3_2212102484_grid_etoday_to", "sensor.solarsynkv3_2212102484_grid_limiter_total_power"});
        put(5, new String[]{"sensor.living_room_temperature"});
        put(6, new String[]{"sensor.tesla_battery_level"});
        put(7, new String[]{"sensor.octopus_energy_electricity_22e5196135_1470001194776_current_accumulative_cost", "sensor.octopus_energy_gas_e6s17516342061_8876054601_current_accumulative_cost"});
    }};

    private HashMap<String, JSONObject> cachedEntityIndex = null;
    private boolean isInitialLoad = true;

    // Home Assistant Configuration
    private static final String HA_BASE_URL = "http://192.168.0.180:8123";
    private static final String HA_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI3MmJhYWRlOWI5YzY0MTA3YjQzYmQ1YzAxZTdkYTdkYyIsImlhdCI6MTc3MzY1NzU0OCwiZXhwIjoyMDg5MDE3NTQ4fQ.X_psjXXzLfiMDRkur8Xg32vn6B0-Dus_9jcLwJmvZ_w";

    // Home Assistant Entity IDs
    private static final String ENTITY_PV1_POWER = "sensor.solarsynkv3_2212102484_pv_mppt0_power";
    private static final String ENTITY_PV2_POWER = "sensor.solarsynkv3_2212102484_pv_mppt1_power";
    private static final String ENTITY_PV1_VOLTAGE = "sensor.solarsynkv3_2212102484_pv_mppt0_voltage";
    private static final String ENTITY_PV1_CURRENT = "sensor.solarsynkv3_2212102484_pv_mppt0_current";
    private static final String ENTITY_PV2_VOLTAGE = "sensor.solarsynkv3_2212102484_pv_mppt1_voltage";
    private static final String ENTITY_PV2_CURRENT = "sensor.solarsynkv3_2212102484_pv_mppt1_current";
    private static final String ENTITY_DAILY_PV_ENERGY = "sensor.solarsynkv3_2212102484_pv_etoday";
    private static final String ENTITY_INVERTER_POWER = "sensor.solarsynkv3_2212102484_inverter_power";
    private static final String ENTITY_INVERTER_VOLTAGE = "sensor.solarsynkv3_2212102484_inverter_voltager_phase_0";
    private static final String ENTITY_INVERTER_CURRENT = "sensor.solarsynkv3_2212102484_inverter_current_phase_0";
    private static final String ENTITY_LOAD_FREQUENCY = "sensor.solarsynkv3_2212102484_load_frequency";
    private static final String ENTITY_ESSENTIAL_POWER = "";
    private static final String ENTITY_NONESSENTIAL_POWER = "";
    private static final String ENTITY_AUX_POWER = "sensor.sunsynk_aux_power";
    private static final String ENTITY_GRID_POWER = "sensor.solarsynkv3_2212102484_grid_pac";
    private static final String ENTITY_GRID_CT_POWER = "sensor.sunsynk_grid_ct_power";
    private static final String ENTITY_BATTERY_POWER = "sensor.solarsynkv3_2212102484_battery_power";
    private static final String ENTITY_BATTERY_POWER_INVERTED = "sensor.solarsynkv3_2212102484_battery_power_inverted";
    private static final String ENTITY_BATTERY_SOC = "sensor.solarsynkv3_2212102484_battery_soc";
    private static final String ENTITY_BATTERY_VOLTAGE = "sensor.solarsynkv3_2212102484_battery_voltage";
    private static final String ENTITY_BATTERY_CURRENT = "sensor.solarsynkv3_2212102484_battery_current";
    private static final String ENTITY_DAILY_LOAD_ENERGY = "sensor.solarsynkv3_2212102484_load_daily_used";
    private static final String ENTITY_DAILY_BATTERY_CHARGE = "sensor.solarsynkv3_2212102484_battery_etoday_charge";
    private static final String ENTITY_DAILY_BATTERY_DISCHARGE = "sensor.solarsynkv3_2212102484_battery_etoday_discharge";
    private static final String ENTITY_DAILY_GRID_IMPORT = "sensor.solarsynkv3_2212102484_grid_etoday_from";
    private static final String ENTITY_DAILY_GRID_EXPORT = "sensor.solarsynkv3_2212102484_grid_etoday_to";
    private static final String ENTITY_PRIORITY_LOAD = "switch.sunsynk_toggle_priority_load";
    private static final String ENTITY_GRID_CONNECTED_STATUS = "binary_sensor.sunsynk_grid_connected_status";
    private static final String ENTITY_INVERTER_STATUS = "sensor.solarsynkv3_2212102484_status";

    // HTML Dashboard Template - Loaded from assets/dashboard.html
    // To update: Export from dashboard designer and copy dashboard.html to app/src/main/assets/
    // The designer will encode images as base64 so they work offline
    private String loadHtmlFromAssets() {
        try {
            InputStream is = getAssets().open("dashboard.html");
            int size = is.available();
            byte[] buffer = new byte[size];
            is.read(buffer);
            is.close();
            return new String(buffer, "UTF-8");
        } catch (Exception ex) {
            Log.e(TAG, "Error loading dashboard.html from assets", ex);
            return "<html><body><h1>Error loading dashboard</h1></body></html>";
        }
    }

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Enable ADB over TCP on port 5555 for remote debugging
        enableAdbOverTcp();

        getWindow().setFlags(
                WindowManager.LayoutParams.FLAG_FULLSCREEN,
                WindowManager.LayoutParams.FLAG_FULLSCREEN
        );
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        webView = new WebView(this);
        webView.setWebViewClient(new WebViewClient());

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setSupportZoom(false);
        settings.setBuiltInZoomControls(false);
        settings.setCacheMode(WebSettings.LOAD_NO_CACHE);

        webView.setVerticalScrollBarEnabled(false);
        webView.setHorizontalScrollBarEnabled(false);

        setContentView(webView);

        // Load HTML from assets file instead of static strings
        // Replace placeholders with actual values
        String html = loadHtmlFromAssets()
                .replace("{{HA_BASE_URL}}", HA_BASE_URL)
                .replace("{{HA_TOKEN}}", HA_TOKEN);

        webView.loadDataWithBaseURL("file:///android_asset/", html, "text/html", "UTF-8", null);
        Log.d(TAG, "WebView loaded, USE_JS_REFRESH=" + USE_JS_REFRESH);
        logEvent("INFO", "MainActivity created; WebView initialized");
        logEvent("INFO", "File logging enabled at " + new File(getFilesDir(), LOG_FILE_NAME).getAbsolutePath());
        startLogServer();
    }

    private final Runnable refreshRunnable = new Runnable() {
        public void run() {
            refreshScheduled = false;
            logEvent("INFO", "refreshRunnable invoked on thread=" + Thread.currentThread().getName() + ", USE_JS_REFRESH=" + USE_JS_REFRESH);
            if (!USE_JS_REFRESH) {
                logEvent("INFO", "Refresh cycle starting");
                fetchAndUpdate();
            }
        }
    };

    private void scheduleRefresh(long delayMs, String reason) {
        handler.removeCallbacks(refreshRunnable);
        refreshScheduled = true;
        logEvent("INFO", "Scheduling refresh in " + delayMs + " ms; reason=" + reason);
        handler.postDelayed(refreshRunnable, delayMs);
    }

    private void cancelRefresh(String reason) {
        if (refreshScheduled) {
            logEvent("INFO", "Cancelling scheduled refresh; reason=" + reason);
        }
        handler.removeCallbacks(refreshRunnable);
        refreshScheduled = false;
    }

    /**
     * Enables ADB over TCP on port 5555 for remote debugging.
     * Requires root access on the device.
     */
    private void enableAdbOverTcp() {
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    Log.d(TAG, "Attempting to enable ADB over TCP on port 5555");
                    
                    // Execute commands as root to enable ADB over TCP
                    executeRootCommand("setprop service.adb.tcp.port 5555");
                    executeRootCommand("stop adbd");
                    executeRootCommand("start adbd");
                    
                    Log.d(TAG, "ADB over TCP enabled on port 5555");
                    logEvent("INFO", "ADB over TCP enabled on port 5555");
                } catch (Exception e) {
                    Log.e(TAG, "Failed to enable ADB over TCP", e);
                    logEvent("ERROR", "Failed to enable ADB over TCP: " + e.getMessage());
                }
            }
        }).start();
    }

    /**
     * Executes a command with root privileges.
     * @param command The command to execute
     */
    private void executeRootCommand(String command) throws Exception {
        Process process = null;
        try {
            process = Runtime.getRuntime().exec("su");
            OutputStream os = process.getOutputStream();
            os.write((command + "\n").getBytes());
            os.write("exit\n".getBytes());
            os.flush();
            os.close();
            
            process.waitFor();
            
            // Read output for debugging
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            String line;
            while ((line = reader.readLine()) != null) {
                Log.d(TAG, "Root command output: " + line);
            }
            reader.close();
            
            // Read error stream
            BufferedReader errorReader = new BufferedReader(new InputStreamReader(process.getErrorStream()));
            while ((line = errorReader.readLine()) != null) {
                Log.e(TAG, "Root command error: " + line);
            }
            errorReader.close();
            
        } finally {
            if (process != null) {
                process.destroy();
            }
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (!USE_JS_REFRESH) {
            scheduleRefresh(3000, "onResume initial refresh");
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        cancelRefresh("onPause");
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        cancelRefresh("onDestroy");
        if (logServerSocket != null && !logServerSocket.isClosed()) {
            try { logServerSocket.close(); } catch (Exception ignored) {}
        }
    }

    @Override
    public void onBackPressed() {
        // Disable back button
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (webView != null) {
            webView.reload();   // full page reload
            logEvent("INFO", "Key press detected: forced WebView reload");
        }
        return true; // consume the key
    }

    private void fetchAndUpdate() {
        logEvent("INFO", "fetchAndUpdate: requesting Home Assistant states");
        Thread t = new Thread(new Runnable() {
            public void run() {
                HttpURLConnection conn = null;
                try {
                    // Call Home Assistant API to get all states
                    URL url = new URL(HA_BASE_URL + "/api/states");
                    conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("GET");
                    conn.setRequestProperty("Accept", "application/json");
                    conn.setRequestProperty("Authorization", "Bearer " + HA_TOKEN);
                    conn.setConnectTimeout(10000);
                    conn.setReadTimeout(10000);

                    int code = conn.getResponseCode();
                    if (code < 200 || code >= 300) {
                        logEvent("ERROR", "Home Assistant request failed with HTTP " + code);
                        return;
                    }

                    String body = readAll(conn.getInputStream());
                    final JSONArray states = new JSONArray(body);
                    logEvent("INFO", "Home Assistant states fetched successfully; entity count=" + states.length());

                    // Build index of entities
                    final HashMap<String, JSONObject> entityIndex = new HashMap<String, JSONObject>();
                    for (int i = 0; i < states.length(); i++) {
                        JSONObject entity = states.getJSONObject(i);
                        String entityId = entity.optString("entity_id");
                        if (entityId != null && entityId.length() > 0) {
                            entityIndex.put(entityId, entity);
                        }
                    }

                    cachedEntityIndex = entityIndex;

                    runOnUiThread(new Runnable() {
                        public void run() {
                            if (isInitialLoad) {
                                logEvent("INFO", "Initial load: injecting all configured entities");
                                processAndInjectAllData(entityIndex);
                                isInitialLoad = false;
                                // Schedule next update after REFRESH_INTERVAL
                                logEvent("INFO", "Initial load complete; scheduling next refresh in " + (REFRESH_INTERVAL/1000) + " seconds");
                                scheduleRefresh(REFRESH_INTERVAL, "initial load complete");
                            } else {
                                logEvent("INFO", "Starting staggered group update cycle");
                                applyGroupsSequentially(entityIndex, 1);
                            }
                        }
                    });

                } catch (final Exception e) {
                    logEvent("ERROR", "Exception while fetching/updating states", e);
                    runOnUiThread(new Runnable() {
                        public void run() {
                            scheduleRefresh(REFRESH_INTERVAL, "retry after error: " + e.getClass().getSimpleName());
                        }
                    });
                } finally {
                    if (conn != null) {
                        conn.disconnect();
                    }
                }
            }
        });
        t.start();
    }

    // Apply all entities at once (for initial load)
    private void processAndInjectAllData(HashMap<String, JSONObject> index) {
        try {
            logEvent("INFO", "Injecting all entity groups in a single pass");
            // Inject all entities from all groups
            for (HashMap.Entry<Integer, String[]> entry : ENTITY_GROUPS.entrySet()) {
                String[] entities = entry.getValue();
                for (String entityId : entities) {
                    injectEntityValue(index, entityId);
                }
            }

            // Update timestamp
            SimpleDateFormat sdf = new SimpleDateFormat("HH:mm:ss", Locale.US);
            String timestamp = sdf.format(new Date());
            setText("statusText", "Loaded " + timestamp);
            logEvent("INFO", "Initial entity injection completed");

        } catch (Exception e) {
            logEvent("ERROR", "Error during initial entity injection", e);
        }
    }

    // Apply groups one at a time with delays
    private void applyGroupsSequentially(final HashMap<String, JSONObject> index, final int groupNum) {
        if (!ENTITY_GROUPS.containsKey(groupNum)) {
            // All groups done, schedule next refresh
            logEvent("INFO", "All groups applied; scheduling next refresh in " + (REFRESH_INTERVAL/1000) + " seconds");
            SimpleDateFormat sdf = new SimpleDateFormat("HH:mm:ss", Locale.US);
            String timestamp = sdf.format(new Date());
            setText("statusText", "Updated " + timestamp);
            scheduleRefresh(REFRESH_INTERVAL, "group cycle complete");
            return;
        }

        logEvent("INFO", "Applying entity group " + groupNum);
        String[] entities = ENTITY_GROUPS.get(groupNum);
        for (String entityId : entities) {
            injectEntityValue(index, entityId);
        }
        logEvent("INFO", "Group " + groupNum + " applied; entity count=" + entities.length);

        // Schedule next group
        handler.postDelayed(new Runnable() {
            public void run() {
                applyGroupsSequentially(index, groupNum + 1);
            }
        }, GROUP_DELAY);
    }

    private void injectEntityValue(HashMap<String, JSONObject> index, String entityId) {
        JSONObject entity = index.get(entityId);
        if (entity == null) {
            logEvent("WARN", "Configured entity missing from response: " + entityId);
            return;
        }

        String state = entity.optString("state");
        if (state == null || state.equals("unknown") || state.equals("unavailable")) {
            logEvent("WARN", "Entity skipped due to unavailable/unknown state: " + entityId);
            return;
        }

        // Convert entity ID to element ID (replace . with _)
        String elementId = entityId.replace(".", "_");

        // Apply custom formatting for specific sensors
        String value = formatEntityValue(entityId, state, entity, false);

        setText(elementId, value);
        logEvent("INFO", "Updated UI element for entity: " + entityId);

        // For grid export, also update the formatted element with _25 suffix
        if (entityId.equals("sensor.solarsynkv3_2212102484_grid_etoday_to")) {
            setText(elementId + "_25", value);

            String originalValue = formatEntityValue(entityId, state, entity, true);
            setText(elementId, originalValue);
            logEvent("INFO", "Updated alternate display element for grid export");
        }
    }

    private String formatEntityValue(String entityId, String state, JSONObject entity, boolean keepOriginalUnit) {
        // Custom formatting for Octopus Energy cost sensors (1.23 GBP -> £1.23)
        if (entityId.equals("sensor.octopus_energy_gas_e6s17516342061_8876054601_current_accumulative_cost") ||
                entityId.equals("sensor.octopus_energy_electricity_22e5196135_1470001194776_current_accumulative_cost")) {
            try {
                double cost = Double.parseDouble(state);
                return String.format("£%.2f", cost);
            } catch (NumberFormatException e) {
                logEvent("WARN", "Failed to parse cost value", e);
                return state;
            }
        }

        // Custom formatting for grid export (multiply kWh by 0.12 to get £)
        if (entityId.equals("sensor.solarsynkv3_2212102484_grid_etoday_to") && !keepOriginalUnit) {
            try {
                double kwh = Double.parseDouble(state);
                double pence = kwh * 0.12;
                return String.format("£%.2f", pence);
            } catch (NumberFormatException e) {
                logEvent("WARN", "Failed to parse grid export value", e);
                return state;
            }
        }

        // Default formatting with unit
        JSONObject attributes = entity.optJSONObject("attributes");
        String unit = "";
        if (attributes != null) {
            unit = attributes.optString("unit_of_measurement", "");
        }

        // Convert W to kW
        if (unit.equals("W") || unit.equals("w")) {
            try {
                double watts = Double.parseDouble(state);
                double kilowatts = watts / 1000.0;
                return String.format("%.2f kW", kilowatts);
            } catch (NumberFormatException e) {
                logEvent("WARN", "Failed to parse power value", e);
                // Fall through to default formatting
            }
        }

        if (unit.length() > 0) {
            unit = " " + unit;
        }
        return state + unit;
    }

    private void setText(String id, String value) {
        String js = "setText('" + escapeJs(id) + "','" + escapeJs(value) + "')";
        webView.loadUrl("javascript:" + js);
    }

    private String readAll(InputStream input) throws Exception {
        BufferedReader reader = null;
        try {
            reader = new BufferedReader(new InputStreamReader(input, "UTF-8"));
            StringBuffer sb = new StringBuffer();
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line);
            }
            return sb.toString();
        } finally {
            if (reader != null) {
                reader.close();
            }
            if (input != null) {
                input.close();
            }
        }
    }

    private String escapeJs(String s) {
        if (s == null) return "";
        s = s.replace("\\", "\\\\");
        s = s.replace("'", "\\'");
        return s;
    }

    private void startLogServer() {
        new Thread(new Runnable() {
            public void run() {
                try {
                    logServerSocket = new ServerSocket(8080);
                    logEvent("INFO", "Log server started on port 8080");
                    while (!logServerSocket.isClosed()) {
                        try {
                            Socket client = logServerSocket.accept();
                            serveLogRequest(client);
                        } catch (Exception e) {
                            if (!logServerSocket.isClosed()) {
                                logEvent("ERROR", "Log server accept error", e);
                            }
                        }
                    }
                } catch (Exception e) {
                    logEvent("ERROR", "Failed to start log server", e);
                }
            }
        }).start();
    }

    private void serveLogRequest(Socket client) {
        try {
            // Drain the HTTP request
            InputStream in = client.getInputStream();
            byte[] reqBuf = new byte[4096];
            in.read(reqBuf);

            File logFile = new File(getFilesDir(), LOG_FILE_NAME);
            byte[] bodyBytes;
            if (logFile.exists()) {
                FileInputStream fis = new FileInputStream(logFile);
                bodyBytes = new byte[(int) logFile.length()];
                fis.read(bodyBytes);
                fis.close();
            } else {
                bodyBytes = "(log file not found)".getBytes("UTF-8");
            }

            OutputStream out = client.getOutputStream();
            String header = "HTTP/1.0 200 OK\r\n"
                    + "Content-Type: text/plain; charset=UTF-8\r\n"
                    + "Content-Length: " + bodyBytes.length + "\r\n"
                    + "Connection: close\r\n"
                    + "\r\n";
            out.write(header.getBytes("UTF-8"));
            out.write(bodyBytes);
            out.flush();
        } catch (Exception e) {
            logEvent("ERROR", "Error serving log request", e);
        } finally {
            try { client.close(); } catch (Exception ignored) {}
        }
    }

    private void logEvent(String level, String message) {
        logEvent(level, message, null);
    }

    private synchronized void logEvent(String level, String message, Throwable throwable) {
        String timestamp = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS", Locale.US).format(new Date());
        String line = timestamp + " [" + level + "] " + message;

        if ("ERROR".equals(level)) {
            if (throwable != null) {
                Log.e(TAG, message, throwable);
            } else {
                Log.e(TAG, message);
            }
        } else if ("WARN".equals(level)) {
            if (throwable != null) {
                Log.w(TAG, message, throwable);
            } else {
                Log.w(TAG, message);
            }
        } else {
            Log.d(TAG, message);
        }

        File logFile = new File(getFilesDir(), LOG_FILE_NAME);
        try {
            rotateLogIfNeeded(logFile);
            FileWriter writer = new FileWriter(logFile, true);
            writer.write(line);
            if (throwable != null) {
                writer.write(" | " + throwable.getClass().getSimpleName() + ": " + String.valueOf(throwable.getMessage()));
            }
            writer.write("\n");
            writer.close();
        } catch (Exception ioe) {
            Log.e(TAG, "Failed to write log file", ioe);
        }
    }

    private void rotateLogIfNeeded(File logFile) {
        if (logFile.exists() && logFile.length() >= LOG_FILE_MAX_BYTES) {
            File backup = new File(getFilesDir(), LOG_FILE_NAME + ".1");
            if (backup.exists()) {
                backup.delete();
            }
            logFile.renameTo(backup);
        }
    }
}