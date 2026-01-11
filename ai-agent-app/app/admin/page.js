"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "./Component/nav";
import { LogoutButton } from "./Component/logout";
import styles from "./page.module.css";

function MetricCard({ title, subtitle, children, footer, loading, error }) {
  return (
    <section className={styles.card}>
      <div className={styles.cardTop}>
        <div>
          <h2 className={styles.cardTitle}>{title}</h2>
          {subtitle ? <p className={styles.cardSubtitle}>{subtitle}</p> : null}
        </div>
      </div>

      <div className={styles.cardBody}>
        {loading ? (
          <div className={styles.skeletonWrap}>
            <div className={styles.skeletonLine} />
            <div className={styles.skeletonLine} />
            <div className={styles.skeletonLineSmall} />
          </div>
        ) : error ? (
          <p className={styles.errorText}>{error}</p>
        ) : (
          children
        )}
      </div>

      {footer ? <div className={styles.cardFooter}>{footer}</div> : null}
    </section>
  );
}

export default function AdminPage() {
  const r = useRouter();

  const API = useMemo(() => process.env.NEXT_PUBLIC_API_URL, []);

  const [loading, setLoading] = useState(true);
  const [me, setMe] = useState(null);

  const [mLoading, setMLoading] = useState(true);
  const [mError, setMError] = useState("");
  const [orderMetric, setOrderMetric] = useState(null);
  const [handoffMetric, setHandoffMetric] = useState(null);
  const [avgaiMetric, setAvgaiMetric] = useState(null);
  const [avgsessionMetric, setAvgsessionMetric] = useState(null);
  const [ktMetric, setKtMetric] = useState({ a_topic: [], a_key: [] });

  useEffect(() => {
    const check = async () => {
      try {
        const resp = await fetch(API + "/auth/check", { credentials: "include" });
        if (!resp.ok) throw new Error("unauth");
        const data = await resp.json();

        if (data.role !== "admin") {
          if (data.role === "call_center") r.replace("/admin/call");
          return;
        }
        setMe(data);
      } catch {
        r.replace("/admin/login");
      } finally {
        setLoading(false);
      }
    };
    check();
  }, [r, API]);

  const runLLMInsight = async () => {
    try {
      setMLoading(true);
      setMError("");

      const runResp = await fetch(
        process.env.NEXT_PUBLIC_API_URL +
        "/admin/run_llm_insight?limit=100&model_name=gpt-4o-mini",
        {
          method: "POST",
          credentials: "include",
        }
      );

      if (!runResp.ok) throw new Error("run_llm_failed");
      window.location.reload();

    } catch (err) {
      setMError("อัปเดต Keyword & Topic ไม่สำเร็จ");
    } finally {
      setMLoading(false);
    }
  };

  useEffect(() => {
    if (!me) return;

    const fetchMetric = async () => {
      setMLoading(true);
      setMError("");
      try {
        const resp = await fetch(API + "/admin/get_order_complete", {
          credentials: "include",
        });
        const resp2 = await fetch(API + "/admin/get_handoff", {
          credentials: "include",
        });
        const resp3 = await fetch(API + "/admin/avg_ai_con", {
          credentials: "include",
        })
        const resp4 = await fetch(API + "/admin/get_key_top", {
          credentials: "include",
        })
        const resp5 = await fetch(API + "/admin/avg_session_time", {
          credentials: "include",
        })

        if (!resp.ok) throw new Error("fetch_failed");
        if (!resp2.ok) throw new Error("fetch_failed");
        if (!resp3.ok) throw new Error("fetch_failed");
        if (!resp4.ok) throw new Error("fetch_failed");
        if (!resp5.ok) throw new Error("fetch_failed");

        const data = await resp.json();
        const data_handoff = await resp2.json();
        const data_avg_ai_con = await resp3.json();
        const data_kt = await resp4.json();
        const data_avg_session = await resp5.json();

        setOrderMetric(data);
        setHandoffMetric(data_handoff);
        setAvgaiMetric(data_avg_ai_con);
        setAvgsessionMetric(data_avg_session);
        setKtMetric({
          a_topic: Array.isArray(data_kt.a_topic) ? data_kt.a_topic : [],
          a_key: Array.isArray(data_kt.a_key) ? data_kt.a_key : [],
        });

      } catch (e) {
        setMError("โหลดข้อมูลไม่สำเร็จ");
      } finally {
        setMLoading(false);
      }
    };

    fetchMetric();
  }, [me, API]);
  if (!me) return null;

  const completeRate = orderMetric?.complete_rate ?? 0;
  const intentSessions = orderMetric?.intent_sessions ?? 0;
  const aiCreateOrder = orderMetric?.ai_create_order ?? 0;

  const total_sessions = handoffMetric?.total_sessions ?? 0;
  const handoff_sessions = handoffMetric?.handoff_sessions ?? 0;
  const handoff_rate = handoffMetric?.handoff_rate ?? 0;

  const ai_message_count = avgaiMetric?.ai_message_count ?? 0;
  const avg_ai_confident = avgaiMetric?.avg_ai_confident ?? 0.0;

  const session_used = avgsessionMetric?.session_used ?? 0;
  const avg_message_count = avgsessionMetric?.avg_message_count ?? 0;
  const avg_session_duration_sec = avgsessionMetric?.avg_session_duration_sec ?? 0;
  const avg_session_duration_min = avgsessionMetric?.avg_session_duration_min ?? 0;

  return (
    <div className={styles.layout}>
      <Navbar />
      <main className={styles.main}>
        <div className={styles.header}>
          <div>
            <h1 className={styles.title}>Admin Dashboard</h1>
            <p className={styles.subtitle}>Welcome, {me.name}</p>
          </div>
          <LogoutButton>Logout</LogoutButton>
        </div>

        <div className={styles.grid}>
          <MetricCard
            title="อัตราการทำงานสำเร็จ"
            loading={mLoading}
            error={mError}
            footer={
              <div className={styles.footerRow}>
                <button
                  className={styles.ghostBtn}
                  onClick={() => window.location.reload()}
                >
                  Refresh
                </button>
              </div>
            }
          >
            <div className={styles.metricRow}>
              <div className={styles.metricMain}>
                <div className={styles.bigNumber}>{completeRate}%</div>
                <div className={styles.smallLabel}>Completion rate</div>
              </div>

              <div className={styles.metricSide}>
                <div className={styles.kpi}>
                  <div className={styles.kpiValue}>{intentSessions} session</div>
                  <div className={styles.kpiLabel}>Create Order Intent sessions</div>
                </div>
                <div className={styles.kpi}>
                  <div className={styles.kpiValue}>{aiCreateOrder} ครั้ง</div>
                  <div className={styles.kpiLabel}>AI use "create_order"</div>
                </div>
              </div>
            </div>
          </MetricCard>

          <MetricCard
            title="อัตราการส่งเรื่องให้เจ้าหน้าที่"
            loading={mLoading}
            error={mError}
            footer={
              <div className={styles.footerRow}>
                <button
                  className={styles.ghostBtn}
                  onClick={() => window.location.reload()}
                >
                  Refresh
                </button>
              </div>
            }
          >
            <div className={styles.metricRow}>
              <div className={styles.metricMain}>
                <div className={styles.bigNumber}>{handoff_rate}%</div>
                <div className={styles.smallLabel}>Handoff rate</div>
              </div>

              <div className={styles.metricSide}>
                <div className={styles.kpi}>
                  <div className={styles.kpiValue}>{total_sessions} session</div>
                  <div className={styles.kpiLabel}>All Sessions</div>
                </div>
                <div className={styles.kpi}>
                  <div className={styles.kpiValue}>{handoff_sessions} ครั้ง</div>
                  <div className={styles.kpiLabel}>AI use "create_ticket"</div>
                </div>
              </div>
            </div>
          </MetricCard>

          <MetricCard
            title="Average Ai Confident"
            loading={mLoading}
            error={mError}
            footer={
              <div className={styles.footerRow}>
                <button
                  className={styles.ghostBtn}
                  onClick={() => window.location.reload()}
                >
                  Refresh
                </button>
              </div>
            }
          >
            <div className={styles.metricRow}>
              <div className={styles.metricMain}>
                <div className={styles.bigNumber}>{avg_ai_confident}%</div>
                <div className={styles.smallLabel}>Average Ai Confident from {ai_message_count} ai message</div>
              </div>
              <div className={styles.metricSide}>
                <div className={styles.kpi}>
                  <div>AI ตอบกลับทั้งหมด {ai_message_count} ข้อความ</div>
                </div>
                <div className={styles.kpi}>
                  <div>มีค่าเฉลี่ยความมั่นใจอยู่ที่ {avg_ai_confident}%</div>
                </div>
              </div>
            </div>

          </MetricCard>

          <MetricCard
            title="Keyword & Topic"
            loading={mLoading}
            error={mError}
            footer={
              <div className={styles.footerRow}>
                <button
                  className={styles.ghostBtn}
                  onClick={runLLMInsight}
                  disabled={mLoading}
                >
                  {mLoading ? "Updating..." : "Refresh"}
                </button>
              </div>
            }
          >
            <div className={styles.ktWrap}>
              <div className={styles.ktCol}>
                <div className={styles.ktHead}>Top Topics</div>
                <ol className={styles.ktList}>
                  {(ktMetric.a_topic || []).slice(0, 5).map((t, idx) => (
                    <li key={idx} className={styles.ktItem}>
                      {t}
                    </li>
                  ))}
                </ol>
              </div>

              <div className={styles.ktCol}>
                <div className={styles.ktHead}>Top Keywords</div>
                <div className={styles.chips}>
                  {(ktMetric.a_key || []).slice(0, 12).map((k, idx) => (
                    <span key={idx} className={styles.chip}>
                      {k}
                    </span>
                  ))}
                </div>
              </div>
            </div>

          </MetricCard>

          <MetricCard
            title="Average Session Time"
            loading={mLoading}
            error={mError}
            footer={
              <div className={styles.footerRow}>
                <button
                  className={styles.ghostBtn}
                  onClick={() => window.location.reload()}
                >
                  Refresh
                </button>
              </div>
            }
          >
            <div className={styles.metricRow}>
              <div className={styles.metricMain}>
                <div className={styles.bigNumber}>{session_used}</div>
                <div className={styles.smallLabel}>จำนวน Session ทั้งหมด</div>
              </div>
              <div className={styles.metricMain}>
                <div className={styles.bigNumber}>{avg_message_count}</div>
                <div className={styles.smallLabel}>ค่าเฉลี่ยข้อความ ต่อ 1 Session</div>
              </div>
              <div className={styles.metricMain}>
                <div className={styles.bigNumber}>{avg_session_duration_sec}</div>
                <div className={styles.smallLabel}>ค่าเฉลี่ยเวลาต่อ 1 Session (วินาที)</div>
              </div>
              <div className={styles.metricMain}>
                <div className={styles.bigNumber}>{avg_session_duration_min}</div>
                <div className={styles.smallLabel}>ค่าเฉลี่ยเวลาต่อ 1 Session (นาที)</div>
              </div>

            </div>
          </MetricCard>

        </div>
      </main>
    </div>
  );
}
