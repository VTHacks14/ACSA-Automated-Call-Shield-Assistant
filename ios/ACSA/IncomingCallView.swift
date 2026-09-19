import SwiftUI

/// A custom SwiftUI mimic of iOS's incoming-call screen. Deliberately NOT CallKit/PushKit —
/// that keeps the whole app on the free Apple ID (Personal Team).
struct IncomingCallView: View {
    @EnvironmentObject var monitor: CallMonitor
    let call: CallState

    var body: some View {
        ZStack {
            LinearGradient(colors: [Color(red: 0.16, green: 0.18, blue: 0.24), Color(red: 0.04, green: 0.05, blue: 0.08)],
                           startPoint: .top, endPoint: .bottom)
                .ignoresSafeArea()
            VStack(spacing: 0) {
                VStack(spacing: 6) {
                    Text("mobile").font(.subheadline).foregroundStyle(.white.opacity(0.6))
                    Text(call.callerDisplay ?? "Unknown caller")
                        .font(.system(size: 34, weight: .semibold)).multilineTextAlignment(.center)
                        .minimumScaleFactor(0.6).lineLimit(2)
                    Text("Incoming call").font(.subheadline).foregroundStyle(.white.opacity(0.6))
                }
                .padding(.top, 70).padding(.horizontal, 24)

                Spacer()
                bubble
                Spacer()
            }
        }
    }

    private var bubble: some View {
        VStack(spacing: 18) {
            HStack(spacing: 10) {
                Image(systemName: "shield.lefthalf.filled").foregroundStyle(.green)
                Text("ACSA").font(.headline)
            }
            Text("Would you like ACSA to answer for you?")
                .font(.title3.weight(.medium)).multilineTextAlignment(.center)
            HStack(spacing: 14) {
                choice("No", system: "xmark", tint: Color(white: 0.28)) { monitor.answer(false) }
                choice("Yes", system: "checkmark", tint: .green) { monitor.answer(true) }
            }
        }
        .padding(24)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 28, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 28, style: .continuous).stroke(.white.opacity(0.12)))
        .padding(.horizontal, 24)
    }

    private func choice(_ title: String, system: String, tint: Color, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Label(title, systemImage: system)
                .font(.headline).frame(maxWidth: .infinity).padding(.vertical, 14)
                .background(tint, in: Capsule()).foregroundStyle(.white)
        }
    }
}

struct DeclinedView: View {
    @EnvironmentObject var monitor: CallMonitor
    let call: CallState

    var body: some View {
        ZStack {
            Color(red: 0.05, green: 0.06, blue: 0.08).ignoresSafeArea()
            VStack(spacing: 16) {
                Image(systemName: "phone.arrow.right").font(.system(size: 44)).foregroundStyle(.secondary)
                Text("You passed on ACSA").font(.title3.weight(.semibold))
                Text("\(call.callerDisplay ?? "The caller") is being sent through to your phone.")
                    .foregroundStyle(.secondary).multilineTextAlignment(.center)
                Button("Done") { monitor.dismiss() }.buttonStyle(.borderedProminent).padding(.top, 8)
            }
            .padding(32)
        }
    }
}
