import SwiftUI

/// The app's root view, always: the logo plus a live backend-connection status. It never transitions away on
/// its own. A real call (CallMonitor.current) is layered over it, and it's what you return to when the call
/// is dismissed.
///
/// The background is white, matching the launch screen (project.yml `UILaunchScreen` is plain white) so there's no
/// flash between iOS's launch screen and this view; the logo block then fades in near the top of the screen.
struct SplashView: View {
    @EnvironmentObject var monitor: CallMonitor
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var pulse = false
    @State private var showSettings = false
    @State private var appeared = false

    private static let logoSize = CGSize(width: 300, height: 120)
    /// The logo block starts this far down the full screen height (about 15-20%).
    private static let topFraction = 0.17
    private static let green = Color(red: 0.20, green: 0.78, blue: 0.35)

    /// Reflects reality after launch too: a dropped backend goes back to "Connecting...".
    private var connected: Bool { monitor.hasConnected && monitor.connectionError == nil }

    var body: some View {
        ZStack {
            splash
            if let call = monitor.current {
                CallFlowView(call: call)
                    .id(call.callSid) // fresh per-call state (e.g. the verdict-screen flag)
                    .transition(.opacity)
                    .zIndex(1)
            }
        }
        .animation(.easeInOut(duration: 0.35), value: monitor.current?.callSid)
    }

    private var splash: some View {
        ZStack(alignment: .topTrailing) {
            Color.white.ignoresSafeArea()
            GeometryReader { geo in
                VStack(spacing: -6) { // tucks the status line up under the tagline (the image has its own margin)
                    Image("acsa_full_logo")
                        .resizable().scaledToFit()
                        .frame(width: Self.logoSize.width, height: Self.logoSize.height)
                        .accessibilityLabel("ACSA, Automated Call Shield Assistant")
                    statusRow
                }
                .frame(maxWidth: .infinity)
                .padding(.top, geo.size.height * Self.topFraction)
                .opacity(appeared ? 1 : 0)
            }
            .ignoresSafeArea() // fractions are of the full screen height, not the safe area
            Button { showSettings = true } label: {
                Image(systemName: "gearshape").font(.title3).foregroundStyle(Theme.muted).padding(16)
            }
            .accessibilityLabel("Settings")
        }
        .sheet(isPresented: $showSettings) { SettingsView() }
        .onAppear { withAnimation(.easeOut(duration: 0.3)) { appeared = true } }
        // Only while the splash is what's showing; call screens pick their own scheme.
        .preferredColorScheme(monitor.current == nil ? .light : nil)
    }

    private var statusRow: some View {
        HStack(spacing: 10) {
            statusDot
            Text(connected ? "Connected" : "Connecting...")
                .font(.subheadline.weight(.medium))
                .foregroundStyle(Theme.muted)
        }
        .accessibilityElement(children: .combine)
    }

    private var statusDot: some View {
        let color = connected ? Self.green : Theme.teal
        return ZStack {
            Circle()
                .fill(color.opacity(0.35))
                .frame(width: 14, height: 14)
                .scaleEffect(pulse ? 2.0 : 1.0)
                .opacity(pulse ? 0 : 0.9)
            Circle()
                .fill(color)
                .frame(width: 12, height: 12)
        }
        .frame(width: 26, height: 26)
        .animation(.easeInOut(duration: 0.3), value: connected)
        .onAppear {
            guard !reduceMotion else { return }
            withAnimation(.easeOut(duration: 1.3).repeatForever(autoreverses: false)) { pulse = true }
        }
    }
}
