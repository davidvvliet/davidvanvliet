"use client";

import AsciiResume from "./AsciiResume";
import MobileResume from "./MobileResume";
import { useIsMobile } from "./useIsMobile";

export default function ResumeView() {
  return useIsMobile() ? <MobileResume /> : <AsciiResume />;
}
