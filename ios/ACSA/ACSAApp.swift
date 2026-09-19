import SwiftUI

@main
struct ACSAApp: App {
    @StateObject private var monitor = CallMonitor()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(monitor)
                .preferredColorScheme(.dark)
                // Polling only runs while foregrounded — no push, so a locked/backgrounded app
                // won't see calls. That's the known, accepted tradeoff (free Apple ID).
                .onChange(of: scenePhase) { _, phase in
                    phase == .active ? monitor.start() : monitor.stop()
                }
                .onAppear { monitor.start() }
        }
    }
}
