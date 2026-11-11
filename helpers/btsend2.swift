// btsend2 — write a file to a Bluetooth device over RFCOMM (macOS).
//
// Usage: btsend2 <address> <file> [channel]     (channel defaults to 1)
//
// The synchronous IOBluetooth open fails against the M9 (kIOReturnError), so the
// channel is opened asynchronously and the work happens in the delegate while a
// run loop spins. Prints "wrote N" on success; exits non-zero on failure.
// Build: swiftc -O -o m9printer/bin/btsend2 helpers/btsend2.swift
import Foundation
import IOBluetooth

let args = CommandLine.arguments
guard args.count >= 3 else { print("usage: btsend2 <addr> <file> [channel]"); exit(2) }
let addr = args[1]
guard let data = try? Data(contentsOf: URL(fileURLWithPath: args[2])) else {
  print("can't read \(args[2])"); exit(2)
}
let channelID = BluetoothRFCOMMChannelID(args.count > 3 ? (UInt8(args[3]) ?? 1) : 1)

var done = false
var failed = false

final class Delegate: NSObject, IOBluetoothRFCOMMChannelDelegate {
  let data: Data
  init(_ d: Data) { self.data = d }

  func rfcommChannelOpenComplete(_ ch: IOBluetoothRFCOMMChannel!, status: IOReturn) {
    print("openComplete status=\(status)")
    if status != kIOReturnSuccess { failed = true; done = true; return }
    let mtu = Int(ch.getMTU())
    print("mtu=\(mtu) sending=\(data.count)")
    var off = 0
    data.withUnsafeBytes { (raw: UnsafeRawBufferPointer) in
      let base = UnsafeMutableRawPointer(mutating: raw.baseAddress!)
      while off < data.count {
        let n = min(mtu, data.count - off)
        let r = ch.writeSync(base.advanced(by: off), length: UInt16(n))
        if r != kIOReturnSuccess { print("write fail @\(off): \(r)"); failed = true; break }
        off += n
      }
    }
    print("wrote \(off)")
    // Give the printer a moment to drain its buffer before dropping the link.
    DispatchQueue.main.asyncAfter(deadline: .now() + 3) { ch.close(); done = true }
  }

  func rfcommChannelClosed(_ ch: IOBluetoothRFCOMMChannel!) { print("channelClosed"); done = true }
}

guard let dev = IOBluetoothDevice(addressString: addr) else { print("no device \(addr)"); exit(2) }
_ = dev.openConnection()
let delegate = Delegate(data)
var channel: IOBluetoothRFCOMMChannel?
let res = dev.openRFCOMMChannelAsync(&channel, withChannelID: channelID, delegate: delegate)
print("asyncOpen res=\(res)")
if res != kIOReturnSuccess { exit(3) }

let deadline = Date().addingTimeInterval(30)
while !done && Date() < deadline {
  _ = RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.25))
}
if !done { print("timed out"); exit(4) }
exit(failed ? 1 : 0)
