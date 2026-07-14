const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY;
const POSTHOG_HOST = import.meta.env.VITE_POSTHOG_HOST || "https://us.i.posthog.com";

export function initPostHog() {
  if (!POSTHOG_KEY || window.__posthog_init__) return;
  window.__posthog_init__ = true;

  (function (p, t, h, o, g) {
    p[t] = p[t] || {};
    p[t]._i = [];
    p[t].init = function (i, s, a) {
      function g_(t_, e_) {
        var o_ = e_.split(".");
        2 == o_.length && ((t_ = t_[o_[0]]), (e_ = o_[1])),
          (t_[e_] = function () {
            t_.push([e_].concat(Array.prototype.slice.call(arguments, 0)));
          });
      }
      var f = document.createElement("script");
      (f.crossOrigin = "anonymous"),
        (f.async = !0),
        (f.src =
          s.api_host.replace(".i.posthog.com", "-assets.i.posthog.com") +
          "/static/array.js"),
        document.head.appendChild(f);
      var u = p[t];
      for (
        void 0 !== a ? (u = p[t][a] = []) : (a = "posthog"),
          u.people = u.people || [],
          u.toString = function (e_) {
            var v = "posthog";
            return "posthog" !== a && (v += "." + a), e_ || (v += " (stub)"), v;
          },
          u.people.toString = function () {
            return u.toString(1) + ".people (stub)";
          },
          o =
            "init me ws ys ps bs capture je Di ks register register_once register_for_session unregister unregister_for_session Ps getFeatureFlag getFeatureFlagPayload isFeatureEnabled reloadFeatureFlags updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures on onFeatureFlags onSurveysLoaded onSessionId getSurveys getActiveMatchingSurveys renderSurvey canRenderSurvey canRenderSurveyAsync identify setPersonProperties group resetGroups setPersonPropertiesForFlags resetPersonPropertiesForFlags resetGroupPropertiesForFlags reset get_distinct_id getGroups get_session_id get_session_replay_url alias set_config startSessionRecording stopSessionRecording sessionRecordingStarted captureException loadToolbar get_property getSessionProperty Es $s createPersonProfile Is opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing clear_opt_in_out_capturing Ss debug xs getPageViewId captureTraceFeedback captureTraceMetric".split(
              " "
            ),
          g = 0;
        g < o.length;
        g++
      )
        g_(u, o[g]);
      p[t]._i.push([i, s, a]);
    };
    p[t].__SV = 1;
  })(window, "posthog", POSTHOG_HOST, undefined, undefined);

  window.posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    person_profiles: "identified_only",
    session_recording: {
      recordCrossOriginIframes: true,
      capturePerformance: false,
    },
  });
}