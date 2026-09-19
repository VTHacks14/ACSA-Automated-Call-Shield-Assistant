import SwiftUI

struct ContentView: View {
    @EnvironmentObject var monitor: CallMonitor

    var body: some View {
        ZStack {
            IdleView()
            if let call = monitor.current {
                CallFlowView(call: call)
                    .transition(.opacity.combined(with: .scale(scale: 1.04)))
                    .zIndex(1)
            }
        }
        .animation(.easeInOut(duration: 0.35), value: monitor.current?.callSid)
    }
}

/// Which screen a call is on. Ringing gets the fake incoming-call screen; everything else is the screening view.
struct CallFlowView: View {
    let call: CallState

    var body: some View {
        switch call.status {
        case "ringing": IncomingCallView(call: call)
        case "declined": DeclinedView(call: call)
        default: ScreeningView(call: call)
        }
    }
}
