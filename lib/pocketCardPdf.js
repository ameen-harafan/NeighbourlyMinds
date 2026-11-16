import fs from "fs";
import path from "path";

const BLACK = "#000000";
const WHITE = "#FFFFFF";
const YELLOW = "#FFE14A";

const BADGE_FILES = {
  "speak-slowly": { file: "speak-slowly.jpg", label: "Speak slowly" },
  "need-help": { file: "need-help.jpg", label: "I need help" },
  disoriented: { file: "disoriented.svg", label: "Disoriented" },
};

function withThe(name) {
  if (!name) return "";
  return /^the\s/i.test(name) ? name : `the ${name}`;
}

function landmarkLine(landmark, index) {
  if (landmark.instruction) return `${index + 1}. ${landmark.instruction}`;
  if (landmark.landmark_name) return `${index + 1}. ${withThe(landmark.landmark_name)}`;
  return "";
}

function drawPanel(doc, x, y, w, h) {
  doc.save();
  doc.rect(x, y, w, h).fill(BLACK);
  doc.rect(x + 8, y + 8, w - 16, h - 16).lineWidth(3).stroke(YELLOW);
  doc.restore();
}

function drawDisorientedBadge(doc, x, y, size) {
  doc.save();
  doc.circle(x + size / 2, y + size / 2, size / 2 - 2).fill(BLACK);
  doc.circle(x + size / 2, y + size / 2, size / 2 - 2).lineWidth(3).stroke(YELLOW);
  doc.circle(x + size * 0.38, y + size * 0.42, size * 0.1).lineWidth(2).stroke(WHITE);
  doc.fillColor(YELLOW).font("Helvetica-Bold").fontSize(size * 0.28).text("?", x + size * 0.58, y + size * 0.28, {
    width: size * 0.3,
    align: "center",
    lineBreak: false,
  });
  doc.restore();
}

function drawBadge(doc, id, x, y, size) {
  const badge = BADGE_FILES[id];
  if (!badge) return;
  if (id === "disoriented") {
    drawDisorientedBadge(doc, x, y, size);
  } else {
    const filePath = path.join(process.cwd(), "public", "badges", badge.file);
    if (fs.existsSync(filePath)) {
      doc.image(filePath, x, y, { width: size, height: size });
    } else {
      drawDisorientedBadge(doc, x, y, size);
    }
  }
  doc.fillColor(WHITE).font("Helvetica-Bold").fontSize(9).text(badge.label, x - 8, y + size + 4, {
    width: size + 16,
    align: "center",
  });
}

export function drawFoldingPocketCard(doc, data) {
  const pageWidth = doc.page.width;
  const pageHeight = doc.page.height;
  const midX = pageWidth / 2;
  const midY = pageHeight / 2;
  const badges = Array.isArray(data.badges) && data.badges.length
    ? data.badges
    : data.badge
      ? [data.badge]
      : [];
  const landmarks = Array.isArray(data.landmarks) ? data.landmarks.slice(0, 6) : [];
  const shade = Number(data.shadePercentage ?? data.shade_percentage);
  const benches = Number(data.benchCount ?? data.bench_count);

  drawPanel(doc, 0, 0, midX, midY);
  drawPanel(doc, midX, 0, midX, midY);
  drawPanel(doc, 0, midY, midX, midY);
  drawPanel(doc, midX, midY, midX, midY);

  doc.save();
  doc.lineWidth(2).dash(8, { space: 6 }).strokeColor(YELLOW);
  doc.moveTo(midX, 18).lineTo(midX, pageHeight - 18).stroke();
  doc.moveTo(18, midY).lineTo(pageWidth - 18, midY).stroke();
  doc.undash();
  doc.restore();

  doc.fillColor(YELLOW).font("Helvetica-Bold").fontSize(8);
  doc.text("FOLD", 10, midY - 5, { width: 28, lineBreak: false });
  doc.text("FOLD", midX - 14, 6, { width: 28, align: "center", lineBreak: false });

  const pad = 22;
  doc.fillColor(YELLOW).font("Helvetica-Bold").fontSize(18).text("NeighborlyMinds", pad, 26, {
    width: midX - pad * 2,
  });
  doc.fillColor(WHITE).font("Helvetica-Bold").fontSize(13).text("Pocket Independence Card", pad, 48, {
    width: midX - pad * 2,
  });
  doc.fillColor(YELLOW).fontSize(11).text("Front  ·  fold to pocket size", pad, 68, {
    width: midX - pad * 2,
  });

  let y = 92;
  if (data.destination) {
    doc.fillColor(YELLOW).font("Helvetica-Bold").fontSize(11).text("DESTINATION", pad, y, { width: midX - pad * 2 });
    y = doc.y + 2;
    doc.fillColor(WHITE).font("Helvetica-Bold").fontSize(13).text(data.destination, pad, y, {
      width: midX - pad * 2,
    });
    y = doc.y + 8;
  }

  if (data.plannedTiming) {
    doc.fillColor(YELLOW).font("Helvetica-Bold").fontSize(11).text("PLANNED WALK TIME", pad, y, { width: midX - pad * 2 });
    y = doc.y + 2;
    doc.fillColor(WHITE).font("Helvetica-Bold").fontSize(12).text(data.plannedTiming, pad, y, {
      width: midX - pad * 2,
    });
    y = doc.y + 8;
  }

  doc.fillColor(YELLOW).font("Helvetica-Bold").fontSize(11).text("EMERGENCY CONTACT", pad, y, { width: midX - pad * 2 });
  y = doc.y + 2;
  doc.fillColor(WHITE).font("Helvetica").fontSize(14).text(data.emergencyContact || "Not written yet", pad, y, {
    width: midX - pad * 2,
  });
  y = doc.y + 8;
  doc.fillColor(YELLOW).font("Helvetica-Bold").fontSize(11).text("ABOUT ME", pad, y, { width: midX - pad * 2 });
  y = doc.y + 2;
  doc.fillColor(WHITE).font("Helvetica").fontSize(12).text(data.conditions || "Early-stage dementia", pad, y, {
    width: midX - pad * 2,
  });

  doc.fillColor(YELLOW).font("Helvetica-Bold").fontSize(16).text("Landmark checklist", midX + pad, 28, {
    width: midX - pad * 2,
  });
  let listY = 58;
  if (landmarks.length === 0) {
    doc.fillColor(WHITE).fontSize(14).text("No saved landmark checklist yet.", midX + pad, listY, {
      width: midX - pad * 2,
    });
  } else {
    landmarks.forEach((landmark, index) => {
      doc.fillColor(WHITE).font("Helvetica-Bold").fontSize(13).text(landmarkLine(landmark, index), midX + pad, listY, {
        width: midX - pad * 2,
        height: 48,
        ellipsis: true,
      });
      listY = doc.y + 8;
    });
  }

  doc.fillColor(YELLOW).font("Helvetica-Bold").fontSize(16).text("Support badges", pad, midY + 24, {
    width: midX - pad * 2,
  });
  doc.fillColor(WHITE).fontSize(12).text("Show this side if you need help.", pad, midY + 48, {
    width: midX - pad * 2,
  });
  if (badges.length === 0) {
    doc.fillColor(WHITE).fontSize(14).text("No badge selected.", pad, midY + 80, {
      width: midX - pad * 2,
    });
  } else {
    badges.slice(0, 3).forEach((id, index) => {
      drawBadge(doc, id, pad + index * 88, midY + 84, 64);
    });
  }

  // Panel 4: Comfort & Daytime Sensory Conditions
  doc.fillColor(YELLOW).font("Helvetica-Bold").fontSize(16).text("Comfort & Sensory Plan", midX + pad, midY + 24, {
    width: midX - pad * 2,
  });

  let comfortY = midY + 50;

  // 1. Walk Window
  doc.fillColor(YELLOW).font("Helvetica-Bold").fontSize(10).text("WALK WINDOW", midX + pad, comfortY, { width: midX - pad * 2 });
  comfortY = doc.y + 2;
  const timingText = data.plannedTiming || "Daytime walk (9:00 AM – 5:00 PM)";
  doc.fillColor(WHITE).font("Helvetica-Bold").fontSize(12).text(timingText, midX + pad, comfortY, { width: midX - pad * 2 });
  comfortY = doc.y + 6;

  // 2. Sound Environment
  doc.fillColor(YELLOW).font("Helvetica-Bold").fontSize(10).text("SOUND ENVIRONMENT", midX + pad, comfortY, { width: midX - pad * 2 });
  comfortY = doc.y + 2;
  let noiseText = "Calm daytime baseline (no sensor nearby)";
  if (data.noiseLevel || (data.decibels !== undefined && data.decibels !== null && !isNaN(Number(data.decibels)))) {
    const dbStr = Number.isFinite(Number(data.decibels)) ? ` · ${Number(data.decibels).toFixed(0)} dB` : "";
    noiseText = `${data.noiseLevel || "Low"} Noise${dbStr}`;
  }
  doc.fillColor(WHITE).font("Helvetica-Bold").fontSize(12).text(noiseText, midX + pad, comfortY, { width: midX - pad * 2 });
  comfortY = doc.y + 6;

  // 3. Footpath Traffic
  doc.fillColor(YELLOW).font("Helvetica-Bold").fontSize(10).text("FOOTPATH TRAFFIC", midX + pad, comfortY, { width: midX - pad * 2 });
  comfortY = doc.y + 2;
  let crowdText = "Standard daytime pedestrian flow";
  if (data.crowdLevel || (data.pedestrianCount !== undefined && data.pedestrianCount !== null && !isNaN(Number(data.pedestrianCount)))) {
    const countStr = Number.isFinite(Number(data.pedestrianCount)) ? ` · ~${Math.round(Number(data.pedestrianCount))} people/hr` : "";
    crowdText = `${data.crowdLevel || "Light"} Crowds${countStr}`;
  }
  doc.fillColor(WHITE).font("Helvetica-Bold").fontSize(12).text(crowdText, midX + pad, comfortY, { width: midX - pad * 2 });
  comfortY = doc.y + 6;

  // 4. Path Amenities
  doc.fillColor(YELLOW).font("Helvetica-Bold").fontSize(10).text("PATH AMENITIES", midX + pad, comfortY, { width: midX - pad * 2 });
  comfortY = doc.y + 2;
  const shadeStr = Number.isFinite(shade) && shade > 0 ? `${shade.toFixed(0)}% tree shade` : "Continuous tree shade";
  const benchStr = Number.isFinite(benches) && benches > 0 ? `${benches} park benches` : "Resting benches along path";
  doc.fillColor(WHITE).font("Helvetica-Bold").fontSize(12).text(`${shadeStr}  ·  ${benchStr}`, midX + pad, comfortY, { width: midX - pad * 2 });
  comfortY = doc.y + 12;

  doc.fillColor(YELLOW).font("Helvetica-Bold").fontSize(11).text("Straight path. No map needed.", midX + pad, comfortY, {
    width: midX - pad * 2,
  });
  comfortY = doc.y + 3;
  doc.fillColor(WHITE).font("Helvetica").fontSize(10).text(
    "Fold along the yellow lines, then fold in half again. Carry this card in a pocket.",
    midX + pad,
    comfortY,
    { width: midX - pad * 2 }
  );
}
