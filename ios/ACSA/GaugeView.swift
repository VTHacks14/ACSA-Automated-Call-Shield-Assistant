import SwiftUI

/// Left-to-right gauge: green (LIKELY_HUMAN) → yellow (HUMAN_LIKELY_SCAM) → red (AI_SCAM).
/// While `verdict` is nil the marker rests at the far left; when it arrives the marker sweeps to its spot.
struct GaugeView: View {
    let verdict: Verdict?

    var body: some View {
        VStack(spacing: 8) {
            GeometryReader { geo in
                let width = geo.size.width
                ZStack(alignment: .leading) {
                    Capsule()
                        .fill(LinearGradient(colors: [.green, .yellow, .red], startPoint: .leading, endPoint: .trailing))
                        .frame(height: 16)
                        .opacity(verdict == nil ? 0.35 : 1)
                    Capsule().fill(.white).frame(width: 6, height: 32)
                        .shadow(color: .black.opacity(0.4), radius: 3)
                        .offset(x: max(0, (verdict?.position ?? 0) * width - 3))
                        .opacity(verdict == nil ? 0 : 1)
                        .animation(.spring(response: 1.0, dampingFraction: 0.62), value: verdict)
                }
                .frame(height: 32)
            }
            .frame(height: 32)
            HStack {
                Text("Human").frame(maxWidth: .infinity, alignment: .leading)
                Text("Scripted").frame(maxWidth: .infinity, alignment: .center)
                Text("AI").frame(maxWidth: .infinity, alignment: .trailing)
            }
            .font(.caption).foregroundStyle(.secondary)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(verdict.map { "Verdict: \($0.title)" } ?? "Analyzing")
    }
}
