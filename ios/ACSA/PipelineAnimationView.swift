import SwiftUI

/// Decorative "analyzing" animation: four empty circular nodes joined by vertical connectors that fill in,
/// top to bottom, with the MongoDB, ElevenLabs, Resemblyzer and Gemini logomarks — each name appears beside its node
/// as it fills. It is a fixed sequence and always plays all the way through, regardless of which layer decides the
/// call or how fast the backend answers: it has a fixed runtime (`totalDuration`) that nothing shortens, and
/// `onFinished` fires once when it has fully played. (The caller holds the verdict back until then.)
struct PipelineAnimationView: View {
    var onFinished: () -> Void = {}

    /// 0 = all empty ... each step fills the next piece: node 1, link, node 2, link, ... last node.
    @State private var step = 0

    private static let stepDuration = 0.75    // seconds per step
    private static let stepCount = stages.count * 2 - 1   // a node per stage, a link between each pair
    private static let holdAfterLast = 0.9    // lets the last name land before hand-off
    /// The fixed minimum time this animation always takes: 7 x 0.75 + 0.9 = 6.15 s.
    static let totalDuration = stepDuration * Double(stepCount) + holdAfterLast

    private static let nodeSize: CGFloat = 62
    private static let linkHeight: CGFloat = 28
    private static let nameWidth: CGFloat = 150   // label column; wide enough for "Resemblyzer" at title3

    private struct Stage { let asset: String; let name: String; let tint: Color }
    private static let stages = [
        Stage(asset: "logo_mongodb", name: "MongoDB", tint: Color(red: 0x00 / 255, green: 0xED / 255, blue: 0x64 / 255)),
        Stage(asset: "logo_elevenlabs", name: "ElevenLabs", tint: .white),
        // Placeholder waveform glyph (see logo_resemblyzer.imageset) until the real Resemblyzer logo is dropped in.
        Stage(asset: "logo_resemblyzer", name: "Resemblyzer", tint: Color(red: 0xC4 / 255, green: 0xB0 / 255, blue: 0xFF / 255)),
        Stage(asset: "logo_gemini", name: "Gemini", tint: Color(red: 0x8A / 255, green: 0xB4 / 255, blue: 0xF8 / 255)),
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            ForEach(0..<Self.stages.count, id: \.self) { i in
                if i > 0 { link(filled: step >= i * 2) }
                row(i, filled: step >= i * 2 + 1)
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 8)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Analyzing the call")
        .task {
            for next in 1...Self.stepCount {
                try? await Task.sleep(nanoseconds: UInt64(Self.stepDuration * 1_000_000_000))
                if Task.isCancelled { return }
                withAnimation(.easeInOut(duration: 0.5)) { step = next }
            }
            try? await Task.sleep(nanoseconds: UInt64(Self.holdAfterLast * 1_000_000_000))
            if !Task.isCancelled { onFinished() }
        }
    }

    private func row(_ i: Int, filled: Bool) -> some View {
        HStack(spacing: 16) {
            node(i, filled: filled)
            Text(Self.stages[i].name)
                .font(.title3.weight(.semibold)).foregroundStyle(Theme.navy)
                .frame(width: Self.nameWidth, alignment: .leading)
                .opacity(filled ? 1 : 0)
                .offset(x: filled ? 0 : -12) // slides out of the node as it fills
        }
    }

    private func node(_ i: Int, filled: Bool) -> some View {
        ZStack {
            Circle().fill(filled ? Theme.navy : Color.white)
            Circle().stroke(filled ? Theme.teal : Theme.muted.opacity(0.45), lineWidth: 2)
            Image(Self.stages[i].asset)
                .renderingMode(.template)
                .resizable().scaledToFit()
                .frame(width: Self.nodeSize * 0.46, height: Self.nodeSize * 0.46)
                .foregroundStyle(Self.stages[i].tint)
                .scaleEffect(filled ? 1 : 0.4)
                .opacity(filled ? 1 : 0)
        }
        .frame(width: Self.nodeSize, height: Self.nodeSize)
    }

    private func link(filled: Bool) -> some View {
        ZStack(alignment: .top) {
            Capsule().fill(Theme.muted.opacity(0.25))
            Capsule().fill(Theme.teal).scaleEffect(y: filled ? 1 : 0, anchor: .top)
        }
        .frame(width: 4, height: Self.linkHeight)
        .padding(.leading, Self.nodeSize / 2 - 2) // centered under the node column
    }
}
