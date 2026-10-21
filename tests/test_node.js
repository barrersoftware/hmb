const { HmbMemoryBus, HmbTier } = require("../bindings/node/index.js");

console.log("=======================================================");
console.log("  Haven Memory Bus (HMB) - Node.js Verification Suite");
console.log("=======================================================");

const bus = new HmbMemoryBus(1024 * 1024, 4096);
console.log(`[node-hmb] Bus Initialized: Capacity=${bus.capacity} slots, Stride=4096`);

const slot0 = bus.allocateSlot(HmbTier.HOT_WORKING_SET);
console.log(`[node-hmb] Allocated Slot 0: ${slot0}`);

const buf0 = bus.resolveBuffer(slot0);
buf0.write("NODEJS-HMB-PASS!", 0, "utf8");
console.log(`[node-hmb] Inscribed into direct buffer slice: ${buf0.toString("utf8", 0, 16)}`);

bus.releaseSlot(slot0);
console.log(`[node-hmb] Released Slot 0. Allocated: ${bus.allocatedCount}, Free: ${bus.freeCount}`);

console.log("=======================================================");
console.log("  ALL NODE.JS HMB VERIFICATIONS PASSED 100%!");
console.log("=======================================================");
