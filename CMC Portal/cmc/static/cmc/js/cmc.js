// cmc/static/cmc/js/cmc.js

// Dynamic bearing columns in vibration entry form
function vibrationForm() {
  return {
    bearingPoints: [],    // loaded from equipment on selection
    customPoints: [],     // user-added extra bearing points

    loadEquipmentBearings(equipmentId) {
      if (!equipmentId) {
        this.bearingPoints = [];
        return;
      }
      fetch(`/api/equipment-bearing-points/?equipment_id=${equipmentId}`)
        .then(r => r.json())
        .then(data => {
          this.bearingPoints = data.bearing_points;
        });
    },

    addBearingPoint() {
      this.customPoints.push({
        id: 'new_' + Date.now(),
        label: '',
        bearing_no: '',
        horizontal_r1: '',
        vertical_r2: '',
        axial: '',
      });
    },

    removeBearingPoint(id) {
      this.customPoints = this.customPoints.filter(p => p.id !== id);
    },

    allPoints() {
      return [...this.bearingPoints, ...this.customPoints];
    }
  };
}

// PM Schedule cell click handling
function scheduleCellState(equipmentId, day, currentStatus) {
  return {
    status: currentStatus,
    open: false,

    init() {
      // Setup state if needed
    },

    updateStatus(newStatus) {
      this.status = newStatus;
      this.open = false;
    }
  };
}
