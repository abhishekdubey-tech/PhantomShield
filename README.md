# 🛡️ PhantomShield
### Cyber Deception & Intrusion Intelligence

**Turn an intruder’s curiosity into a trail of evidence.**

PhantomShield is a cybersecurity hackathon prototype that demonstrates how decoy digital assets can reveal suspicious activity. It creates a fictional corporate environment where interactions with fake files, credentials, and monitored endpoints generate security events, alerts, and incident reports.

**DECEIVE → DETECT → TRACE → ALERT → INVESTIGATE**

## The Problem

An isolated security alert rarely tells the complete story. Investigators need to understand what was accessed, how activity progressed, and which actions belong to the same incident.

PhantomShield demonstrates how cyber deception can create detection signals and connect them into an understandable investigation.

## How It Works

1. **Deceive:** Place fictional confidential files, nonfunctional credentials, and monitored endpoint objects inside a simulated network.
2. **Detect:** Evaluate interactions using four explainable detection rules.
3. **Trace:** Connect recorded activity using a shared session ID.
4. **Alert:** Generate severity-ranked alerts that operators can acknowledge or resolve.
5. **Investigate:** Reconstruct the timeline and generate a report from stored evidence.

All activity takes place in a safe simulation. No real scanning, exploitation, or credential harvesting occurs.

## Key Features

- **Cinematic introduction:** Five storytelling stages explain the threat, network, deception, detection, and defense.
- **Live dashboard:** Metrics and visualizations update from recorded simulation data.
- **Deception Lab:** Interact with four decoy files, two fake credential records, and four monitored endpoints.
- **Attack Simulator:** Run Suspicious File Access, Credential Discovery, or Multi-Stage Intrusion.
- **Network Monitor:** Inspect six simulated nodes and their recorded activity.
- **Threat Alerts:** Search, filter, acknowledge, and resolve alerts.
- **Incident Timeline:** Follow the sequence of events within a session.
- **Incident Reports:** Generate evidence-based summaries, export JSON, and print or save as PDF.
- **Persistent storage:** Use Neon PostgreSQL online or SQLite locally.
- **Accessible design:** Responsive layouts and reduced-motion support.

## Detection Rules

| Rule | Trigger | Severity |
|------|---------|----------|
| R1 | Opening a confidential decoy file | Medium |
| R2 | Accessing fictional credentials | High |
| R3 | Accessing multiple distinct monitored assets in one session | At least High |
| R4 | Accessing an endpoint after credential discovery | Critical |

Escalation takes precedence. Each event records its primary detection rule.

## Try the Live Demo

**Live application:** https://phantom-shield.vercel.app/

1. Click **Launch Live Demo**.
2. Select **Multi-Stage Intrusion**.
3. Click **Launch Simulated Intrusion**.
4. Watch events, alerts, and affected network nodes update.
5. Open **Incident Timeline** to inspect the session.
6. Generate an incident report.

From a clean reset, this scenario produces **5 events, 3 alerts, and 1 critical incident**.

The scroll-driven introduction is illustrative. Scrolling does not create security events or trigger the detection engine.

## Technology Stack

- **Frontend:** HTML5, CSS3, JavaScript
- **Animations:** GSAP and ScrollTrigger
- **Visualizations:** SVG
- **Backend:** Python standard-library HTTP handlers and REST APIs
- **Hosted database:** Neon PostgreSQL
- **Database driver:** Psycopg 3
- **Offline database:** SQLite
- **Hosting:** Vercel
- **Version control:** Git and GitHub
- **Testing:** Python unittest

## Architecture

Browser Interaction / Simulation Step
                  ↓
             Python REST API
                  ↓
      Detection Rules + Session History
                  ↓
       PostgreSQL / Local SQLite
                  ↓
   Dashboard → Alerts → Timeline → Report

## Run Locally

Requires Python 3.10 or newer.

```bash
python server.py