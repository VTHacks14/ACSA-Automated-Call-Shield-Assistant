import SwiftUI

/// After Yes: ACSA's greeting as text, then the caller's transcript and the verdict gauge once analysis finishes.
struct ScreeningView: View {
    @EnvironmentObject var monitor: CallMonitor
    let call: CallState

    // Staged reveal so the gauge sweep lands after the transcript, not at the same instant.
    @State private var showTranscript = false
    @State private var gaugeVerdict: Verdict?

    private var isDone: Bool { call.status == "done" }

    var body: some View {
        ZStack {
            Color(red: 0.05, green: 0.06, blue: 0.08).ignoresSafeArea()
            VStack(spacing: 0) {
                header
                ScrollView {
                    VStack(alignment: .leading, spacing: 14) {
                        if let greeting = call.greetingText {
                            bubble(label: "ACSA", text: greeting, tint: .green.opacity(0.18), leading: true)
                        }
                        if call.status == "error" {
                            bubble(label: "Problem", text: call.explanation ?? "Something went wrong analyzing this call.",
                                   tint: .orange.opacity(0.2), leading: true)
                        } else if !isDone {
                            ListeningDots(label: call.status == "processing" ? "Analyzing the response…" : "Listening…")
                        } else if showTranscript, let transcript = call.transcript, !transcript.isEmpty {
                            bubble(label: call.callerDisplay ?? "Caller", text: "“\(transcript)”",
                                   tint: .white.opacity(0.09), leading: false)
                                .transition(.move(edge: .bottom).combined(with: .opacity))
                        }
                    }
                    .padding(20)
                }
                if isDone { verdictPanel.transition(.move(edge: .bottom).combined(with: .opacity)) }
            }
        }
        .onChange(of: call.status, initial: true) { _, status in
            guard status == "done" else { return }
            withAnimation(.easeOut(duration: 0.4)) { showTranscript = true }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.7) { gaugeVerdict = call.verdictKind }
        }
    }

    private var header: some View {
        VStack(spacing: 4) {
            Text(call.callerDisplay ?? "Unknown caller").font(.title2.weight(.semibold))
            Text(statusText).font(.footnote).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity).padding(.top, 28).padding(.bottom, 12)
    }

    private var statusText: String {
        switch call.status {
        case "answered": return "ACSA is on the call"
        case "processing": return "Screening…"
        case "done": return "Screening complete"
        default: return "Call ended"
        }
    }

    private var verdictPanel: some View {
        VStack(spacing: 14) {
            GaugeView(verdict: gaugeVerdict)
            if let verdict = gaugeVerdict {
                Text(verdict.title).font(.title2.weight(.bold)).foregroundStyle(verdict.color)
                    .transition(.opacity)
                if let text = call.explanation {
                    Text(text).font(.callout).foregroundStyle(.secondary).multilineTextAlignment(.center)
                }
            }
            Button("Done") { monitor.dismiss() }.buttonStyle(.borderedProminent).tint(.white.opacity(0.18)).padding(.top, 4)
        }
        .padding(22)
        .frame(maxWidth: .infinity)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 28, style: .continuous))
        .padding(.horizontal, 12).padding(.bottom, 8)
        .animation(.easeInOut, value: gaugeVerdict)
    }

    private func bubble(label: String, text: String, tint: Color, leading: Bool) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label.uppercased()).font(.caption2.weight(.semibold)).foregroundStyle(.secondary)
            Text(text).font(.body)
        }
        .padding(14)
        .background(tint, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
        .frame(maxWidth: .infinity, alignment: leading ? .leading : .trailing)
    }
}

struct ListeningDots: View {
    let label: String
    @State private var phase = 0

    var body: some View {
        HStack(spacing: 10) {
            HStack(spacing: 5) {
                ForEach(0..<3, id: \.self) { i in
                    Circle().fill(.secondary).frame(width: 7, height: 7).opacity(phase == i ? 1 : 0.3)
                }
            }
            Text(label).font(.footnote).foregroundStyle(.secondary)
        }
        .padding(.top, 6)
        .task {
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 350_000_000)
                phase = (phase + 1) % 3
            }
        }
    }
}
