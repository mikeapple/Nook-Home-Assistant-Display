package com.mikeapple.myapplication;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
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
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class MainActivity extends Activity {

    private static final String TAG = "EnergyDashboard";
    private WebView webView;
    private Handler handler = new Handler();

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
    private static final String HA_TOKEN = "..-"; // Replace with your actual long-lived access token from Home Assistant

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
    }

    private Runnable refreshRunnable = new Runnable() {
        public void run() {
            if (!USE_JS_REFRESH) {
                Log.d(TAG, "Refresh cycle starting");
                fetchAndUpdate();
            }
        }
    };

    @Override
    protected void onResume() {
        super.onResume();
        if (!USE_JS_REFRESH) {
            Log.d(TAG, "onResume: Starting initial load in 3 seconds");
            handler.postDelayed(refreshRunnable, 3000);
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        handler.removeCallbacks(refreshRunnable);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        handler.removeCallbacks(refreshRunnable);
    }

    @Override
    public void onBackPressed() {
        // Disable back button
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (webView != null) {
            webView.reload();   // full page reload
        }
        return true; // consume the key
    }

    private void fetchAndUpdate() {
        Log.d(TAG, "fetchAndUpdate: Fetching HA states");
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
                        Log.e(TAG, "HTTP error: " + code);
                        return;
                    }

                    String body = readAll(conn.getInputStream());
                    final JSONArray states = new JSONArray(body);
                    Log.d(TAG, "Fetched " + states.length() + " entities from HA");

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
                                Log.d(TAG, "Initial load: Injecting all entities at once");
                                processAndInjectAllData(entityIndex);
                                isInitialLoad = false;
                                // Schedule next update after REFRESH_INTERVAL
                                Log.d(TAG, "Scheduling next update in " + (REFRESH_INTERVAL/1000) + " seconds");
                                handler.postDelayed(refreshRunnable, REFRESH_INTERVAL);
                            } else {
                                Log.d(TAG, "Starting group-based update cycle");
                                applyGroupsSequentially(entityIndex, 1);
                            }
                        }
                    });

                } catch (Exception e) {
                    Log.e(TAG, "Error fetching data: " + e.getMessage());
                    e.printStackTrace();
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
            Log.d(TAG, "Injecting all entities");
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
            Log.d(TAG, "All entities injected");

        } catch (Exception e) {
            Log.e(TAG, "Error in processAndInjectAllData: " + e.getMessage());
        }
    }

    // Apply groups one at a time with delays
    private void applyGroupsSequentially(final HashMap<String, JSONObject> index, final int groupNum) {
        if (!ENTITY_GROUPS.containsKey(groupNum)) {
            // All groups done, schedule next refresh
            Log.d(TAG, "All groups applied, scheduling next refresh in " + (REFRESH_INTERVAL/1000) + " seconds");
            SimpleDateFormat sdf = new SimpleDateFormat("HH:mm:ss", Locale.US);
            String timestamp = sdf.format(new Date());
            setText("statusText", "Updated " + timestamp);
            handler.postDelayed(refreshRunnable, REFRESH_INTERVAL);
            return;
        }

        Log.d(TAG, "Applying group " + groupNum);
        String[] entities = ENTITY_GROUPS.get(groupNum);
        for (String entityId : entities) {
            injectEntityValue(index, entityId);
        }
        Log.d(TAG, "Group " + groupNum + " applied (" + entities.length + " entities)");

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
            Log.w(TAG, "Entity not found: " + entityId);
            return;
        }

        String state = entity.optString("state");
        if (state == null || state.equals("unknown") || state.equals("unavailable")) {
            Log.w(TAG, "Entity " + entityId + " has invalid state: " + state);
            return;
        }

        // Convert entity ID to element ID (replace . with _)
        String elementId = entityId.replace(".", "_");

        // Apply custom formatting for specific sensors
        String value = formatEntityValue(entityId, state, entity, false);

        setText(elementId, value);
        Log.d(TAG, "Injected " + entityId + " = " + value);

        // For grid export, also update the formatted element with _25 suffix
        if (entityId.equals("sensor.solarsynkv3_2212102484_grid_etoday_to")) {
            setText(elementId + "_25", value);

            String originalValue = formatEntityValue(entityId, state, entity, true);
            setText(elementId, originalValue);
            Log.d(TAG, "Also injected formatted element: " + elementId + "_25");
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
                Log.w(TAG, "Failed to parse cost value: " + state);
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
                Log.w(TAG, "Failed to parse kWh value: " + state);
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
                Log.w(TAG, "Failed to parse watts value: " + state);
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
}