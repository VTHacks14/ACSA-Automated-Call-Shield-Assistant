import SwiftUI

/// One call's screens, in order: native-style ringing screen with the Yes/No bubble -> white screening screen
/// (transcript + animation) -> back on the native-style screen with the verdict bubble.
/// A declined call never gets here: CallMonitor drops it (the caller heard "busy or unavailable").
struct CallFlowView: View {
    let call: CallState
    @State private var showVerdict = false

    var body: some View {
        Group {
            if call.status == "ringing" {
                IncomingCallView(call: call)
            } else if showVerdict {
                VerdictCallView(call: call)
            } else {
                ScreeningView(call: call) { showVerdict = true }
            }
        }
        .animation(.easeInOut(duration: 0.4), value: showVerdict)
        .transition(.opacity)
    }
}
