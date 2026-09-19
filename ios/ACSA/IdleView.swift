import SwiftUI

struct IdleView: View {
    @EnvironmentObject var monitor: CallMonitor
    @State private var showSettings = false
    @State private var pulse = false

    var body: some View {
        ZStack {
            Color(red: 0.05, green: 0.06, blue: 0.08).ignoresSafeArea()
            VStack(spacing: 22) {
                Spacer()
                ZStack {
                    Circle().fill(Color.green.opacity(0.12)).frame(width: 190, height: 190)
                        .scaleEffect(pulse ? 1.15 : 0.9)
                    Image(systemName: "shield.lefthalf.filled")
                        .font(.system(size: 76)).foregroundStyle(.green)
                }
                Text("ACSA").font(.system(size: 34, weight: .bold, design: .rounded))
                Text("Guarding your line").foregroundStyle(.secondary)
                statusPill
                Spacer()
                Text("Keep this app open — it can't wake from the lock screen.")
                    .font(.footnote).foregroundStyle(.tertiary).multilineTextAlignment(.center).padding(.horizontal, 40)
            }
            VStack {
                HStack {
                    Spacer()
                    Button { showSettings = true } label: {
                        Image(systemName: "gearshape").font(.title3).padding(16)
                    }
                    .accessibilityLabel("Settings")
                }
                Spacer()
            }
        }
        .onAppear { withAnimation(.easeInOut(duration: 1.8).repeatForever(autoreverses: true)) { pulse = true } }
        .sheet(isPresented: $showSettings) { SettingsView() }
    }

    private var statusPill: some View {
        let ok = monitor.connectionError == nil && monitor.hasConnected
        return HStack(spacing: 8) {
            Circle().fill(ok ? Color.green : Color.orange).frame(width: 8, height: 8)
            Text(ok ? "Connected to backend" : (monitor.connectionError ?? "Connecting…")).font(.footnote)
        }
        .padding(.horizontal, 14).padding(.vertical, 8)
        .background(.white.opacity(0.07), in: Capsule())
    }
}

struct SettingsView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var url = APIClient.baseURL

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("https://xxxx.ngrok-free.app", text: $url)
                        .textInputAutocapitalization(.never).autocorrectionDisabled().keyboardType(.URL)
                } header: {
                    Text("Backend URL")
                } footer: {
                    Text("ngrok's free tier gives a new URL every restart — paste the current one here.")
                }
            }
            .navigationTitle("Settings")
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { APIClient.baseURL = url; dismiss() }
                }
            }
        }
    }
}
