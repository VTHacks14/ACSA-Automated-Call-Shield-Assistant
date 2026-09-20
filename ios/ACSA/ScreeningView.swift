import SwiftUI

/// After Yes: ACSA's greeting, then — strictly in this order — the caller's transcript, then the decorative
/// analysis animation, then (via `onVerdict`) the verdict screen. White background, same as the splash.
///
///   1. "Listening…" while the caller is being recorded, "Transcribing…" while the backend works.
///   2. The transcript appears the moment the backend has it (it publishes it right after transcription).
///   3. After a short read pause the four-node animation starts. It never starts before or alongside the transcript.
///   4. The animation always plays through in full (fixed runtime). The verdict is held back until it has, AND the
///      result is in — so a fast backend never truncates it, and a slow one just waits on the finished animation.
///
/// Chat layout: ACSA's messages are teal-accented bubbles on the left, the caller's are on the right.
struct ScreeningView: View {
    @EnvironmentObject var monitor: CallMonitor
    let call: CallState
    let onVerdict: () -> Void

    @State private var animationStarted = false
    @State private var animationFinished = false

    private static let readPause: UInt64 = 1_800_000_000      // transcript sits alone this long before the animation
    private static let holdBeforeVerdict: UInt64 = 500_000_000 // beat between the animation finishing and the reveal

    private var isDone: Bool { call.status == "done" }
    private var hasTranscript: Bool { !(call.transcript ?? "").isEmpty }

    var body: some View {
        ZStack {
            Color.white.ignoresSafeArea()
            VStack(spacing: 0) {
                header
                ScrollView {
                    VStack(alignment: .leading, spacing: 14) {
                        if let greeting = call.greetingText {
                            bubble(kind: .acsa, label: "ACSA", text: greeting)
                        }
                        if call.status == "error" {
                            bubble(kind: .problem, label: "Problem",
                                   text: call.explanation ?? "Something went wrong analyzing this call.")
                            doneButton
                        } else {
                            if hasTranscript {
                                bubble(kind: .caller, label: call.callerDisplay ?? "Caller", text: "“\(call.transcript ?? "")”")
                                    .transition(.move(edge: .bottom).combined(with: .opacity))
                            } else if !animationStarted {
                                ListeningDots(label: call.status == "processing" ? "Transcribing…" : "Listening…")
                            }
                            if animationStarted {
                                PipelineAnimationView { animationFinished = true }
                                    .transition(.opacity)
                            }
                        }
                    }
                    .padding(20)
                    .animation(.easeOut(duration: 0.4), value: hasTranscript)
                    .animation(.easeOut(duration: 0.4), value: animationStarted)
                }
            }
        }
        .preferredColorScheme(.light)
        // Start the animation only once the transcript has been on screen for a beat. (No transcript at all — e.g.
        // the number gate ended the call before any audio work — means there's nothing to read first, so go on
        // as soon as the result is in.)
        .task(id: hasTranscript || isDone) {
            guard hasTranscript || isDone, !animationStarted else { return }
            if hasTranscript { try? await Task.sleep(nanoseconds: Self.readPause) }
            if !Task.isCancelled { animationStarted = true }
        }
        .task(id: animationFinished && isDone) {
            guard animationFinished && isDone else { return }
            try? await Task.sleep(nanoseconds: Self.holdBeforeVerdict)
            if !Task.isCancelled { onVerdict() }
        }
    }

    /// Compact chat-style header (avatar beside name/status) so the bubbles keep their room.
    private var header: some View {
        HStack(spacing: 14) {
            CallerAvatar(size: 52)
            VStack(alignment: .leading, spacing: 2) {
                Text(call.callerDisplay ?? "Unknown caller")
                    .font(.title3.weight(.medium)).foregroundStyle(Theme.navy).lineLimit(1).minimumScaleFactor(0.7)
                Text(statusText).font(.subheadline).foregroundStyle(Theme.muted)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading).padding(.horizontal, 20).padding(.top, 16).padding(.bottom, 8)
    }

    private var statusText: String {
        switch call.status {
        case "answered": return "ACSA is on the call"
        case "processing": return animationStarted ? "Analyzing…" : "Screening…"
        case "done": return animationFinished ? "Screening complete" : "Analyzing…"
        default: return "Call ended"
        }
    }

    private var doneButton: some View {
        Button { monitor.dismiss() } label: {
            Text("Done").font(.headline).foregroundStyle(Theme.navy)
                .padding(.horizontal, 36).padding(.vertical, 12)
                .background(Theme.teal, in: Capsule())
        }
        .frame(maxWidth: .infinity).padding(.top, 6)
    }

    private enum BubbleKind { case acsa, caller, problem }

    /// Chat bubble: ACSA and problem notices sit left, the caller sits right. The corner nearest the
    /// sender is tightened for a chat-tail look, and bubbles stop short of the far edge.
    private func bubble(kind: BubbleKind, label: String, text: String) -> some View {
        let leading = kind != .caller
        let problem = Color(red: 0.80, green: 0.35, blue: 0.05) // readable orange on white
        let labelColor: Color = { switch kind { case .acsa: return Theme.navy; case .caller: return Theme.muted; case .problem: return problem } }()
        let fill: Color = { switch kind { case .acsa: return Theme.teal.opacity(0.18); case .caller: return Theme.navy.opacity(0.06); case .problem: return problem.opacity(0.12) } }()
        let border: Color = { switch kind { case .acsa: return Theme.teal; case .caller: return .clear; case .problem: return problem.opacity(0.6) } }()
        let shape = UnevenRoundedRectangle(
            topLeadingRadius: leading ? 6 : 20, bottomLeadingRadius: 20,
            bottomTrailingRadius: 20, topTrailingRadius: leading ? 20 : 6, style: .continuous)
        return HStack(spacing: 0) {
            if !leading { Spacer(minLength: 44) }
            VStack(alignment: .leading, spacing: 4) {
                Text(label.uppercased()).font(.caption.weight(.semibold)).foregroundStyle(labelColor)
                Text(text).font(.body).foregroundStyle(Theme.navy)
            }
            .padding(14)
            .background(fill, in: shape)
            .overlay(shape.stroke(border, lineWidth: 1.2))
            if leading { Spacer(minLength: 44) }
        }
    }
}

struct ListeningDots: View {
    let label: String
    @State private var phase = 0

    var body: some View {
        HStack(spacing: 10) {
            HStack(spacing: 5) {
                ForEach(0..<3, id: \.self) { i in
                    Circle().fill(Theme.teal).frame(width: 7, height: 7).opacity(phase == i ? 1 : 0.3)
                }
            }
            Text(label).font(.subheadline).foregroundStyle(Theme.muted)
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
