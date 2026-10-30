# Phase6 transport-protection coverage audit

Batch M starts at `daa09349715333b47e50cdf7b2392f27292fe391`, branch diskless-v2, after R1 closed. Hardware remains paused/current device stock fastboot. Binary question: do the repository-added accepted root-transport guards protect IPv4 addressing, routing/policy rules or netfilter changes during Android startup?

Answer **NO for the added guards, SOURCE_PROVEN**. This does not assert the complete upstream kernel has no networking policy; it establishes the exact scope of this project's accepted additions.

The accepted configure/verifier allow tracked kernel changes only in board-flo-storage.c and drivers/usb/otg/msm_otg.c (historical working-tree defconfig is ignored). Independent verifier reconstructs the managed source changes exactly. The changes disable SDCC1/eMMC registration, reject active B-peripheral PHY/OTG low-power entry, and reject PM_SUSPEND_PREPARE before freezing/device PM. CONFIG_USB_ETH=y/USB_G_ANDROID=n prevents Android composite-gadget replacement. These additions contain no address/rule/route/netfilter protection. The continuation configures usb0/NBD before handing off, but retains no later networking supervisor. Phase4's real-device power/stress gate remains accepted; it did not execute arbitrary later Android networking transitions.

HOST_FACT: exact golden system SHA a43a7c2def20e5fe3be5404624de8a9c30dea1fe3ff2d2f84a6e8240c4ae1880 was rechecked on the Mac and the real startup files/netd identity resolved read-only:

```text
/system/bin/netd: inode822,479760 bytes
sha256=efb13b1f3b33289d85d2091b5c1c2a07d82fce2ee0e0fd02e879dd7bd833dbaf
/system/etc/init/netd.rc: inode1077,590 bytes
sha256=c558bb07806b29035f4d1093422c0e2afc574d3d15aa27654c3525cf8f2ac4cc
```

The extracted init.rc starts netd in zygote-start and sets fwmark_reflect/tcp_fwmark_accept earlier. Extracted init.flox.rc/USB rc provide exact related inputs. These texts alone do not establish which routing/filter operations the compiled netd executes. R1's netd start near20s and request-flow stop are temporal correlation only; do not claim netd caused the failure yet. Kernel source tree is on the prior Debian build path, not found in the Mac home; no rebuild or Debian access was required in M.

Evidence: `audits/2026-10-30-transport-coverage/` contains the extraction/source-identity report and exact text inputs. No source/runtime image was changed and no hardware command ran in M. No new real-device cause is accepted; Phase1–5 remain frozen. Next binary source/artifact question: does the exact compiled netd's startup policy remove/bypass the ordinary main-table route used by the pre-Android unmarked NBD socket? Establish exact artifact/source linkage or retain UNKNOWN before proposing a one-variable diagnostic. Current hardware pause remains; no automatic boot/rc bypass/transport redesign is authorized.
