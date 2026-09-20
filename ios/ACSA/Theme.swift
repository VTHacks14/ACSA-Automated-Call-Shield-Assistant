import SwiftUI

/// Palette for the call screens (incoming, screening, declined) and the splash's status dot.
enum Theme {
    static let navy = Color(red: 0x11 / 255, green: 0x20 / 255, blue: 0x41 / 255)  // #112041 background
    static let teal = Color(red: 0x69 / 255, green: 0xCB / 255, blue: 0xCE / 255)  // #69CBCE accent
    static let muted = Color(red: 0x58 / 255, green: 0x74 / 255, blue: 0x8D / 255) // #58748D secondary text
    static let text = Color(red: 0.96, green: 0.97, blue: 0.99)                    // near-white primary text

    /// Fill for cards and bubbles: a faint lift off the navy background.
    static let surface = Color.white.opacity(0.06)
}

/// Generic silhouette avatar in a teal ring, with a small ACSA shield badge. No photo, by design.
struct CallerAvatar: View {
    var size: CGFloat = 148
    var pulsing = false

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var pulse = false

    var body: some View {
        ZStack {
            if pulsing {
                Circle()
                    .stroke(Theme.teal.opacity(0.5), lineWidth: 2)
                    .frame(width: size, height: size)
                    .scaleEffect(pulse ? 1.25 : 1.0)
                    .opacity(pulse ? 0 : 0.8)
            }
            Circle().fill(Theme.teal.opacity(0.10)).frame(width: size, height: size)
            Circle().stroke(Theme.teal, lineWidth: 2).frame(width: size, height: size)
            Image(systemName: "person.fill")
                .font(.system(size: size * 0.46))
                .foregroundStyle(Theme.muted)
        }
        .overlay(alignment: .bottomTrailing) {
            Image(systemName: "shield.lefthalf.filled")
                .font(.system(size: size * 0.17, weight: .semibold))
                .foregroundStyle(Theme.teal)
                .frame(width: size * 0.3, height: size * 0.3)
                .background(Theme.navy, in: Circle())
                .overlay(Circle().stroke(Theme.teal, lineWidth: 1.5))
                .offset(x: -size * 0.02, y: -size * 0.02)
        }
        .onAppear {
            guard pulsing, !reduceMotion else { return }
            withAnimation(.easeOut(duration: 1.6).repeatForever(autoreverses: false)) { pulse = true }
        }
        .accessibilityHidden(true)
    }
}
