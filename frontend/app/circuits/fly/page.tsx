import { redirect } from "next/navigation";

// The fin bench now lives on the board's own page.
export default function FlyPage() {
  redirect("/circuits?board=rocket-recorder");
}
