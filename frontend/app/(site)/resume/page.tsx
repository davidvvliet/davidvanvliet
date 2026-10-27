import { Metadata } from "next";
import ResumeView from "../../components/ResumeView";

export const metadata: Metadata = {
  title: "Resume",
  alternates: { canonical: "/resume" },
};

export default function ResumePage() {
  return <ResumeView />;
}
