import type { Metadata } from "next";
import Link from "next/link";

import { PolicyDocument, PolicyParagraph as P, PolicySection } from "../PolicyDocument";
import { TOKENS } from "@/lib/design";

export const metadata: Metadata = {
  title: "Monsi SMS Terms — Sidira",
  description: "Terms for Monsi’s private SMS pilot: voluntary participation, scripted test replies, message frequency, carrier charges, STOP, and support.",
  alternates: { canonical: "https://sidira.ai/monsi/terms" },
};

export default function MonsiTermsPage() {
  return (
    <PolicyDocument title="Monsi SMS Terms" current="terms">
      <PolicySection title="Program and participation">
        <P>Monsi is a personal assistant proof of concept being tested through SMS. The private pilot is limited to invited adult testers and does not involve customers.</P>
        <P>Messages are basic greetings and scripted conversational test replies. The current transport test does not use an AI provider to process message content, and it does not send marketing messages or verification codes.</P>
        <P>Consent is obtained directly before a tester’s number is included. Participation is voluntary, and you may withdraw at any time. Visiting these policy pages does not enroll you or provide consent to receive messages.</P>
      </PolicySection>

      <PolicySection title="Message frequency and charges">
        <P>Message frequency varies with testing activity and participants’ conversations. Testing may include repeated greetings and replies; there is no fixed messaging schedule.</P>
        <P><strong>Message and data rates may apply.</strong> Contact your mobile carrier for information about charges under your plan.</P>
      </PolicySection>

      <PolicySection title="Stopping messages">
        <P><strong>Reply STOP to unsubscribe from Monsi SMS messages and withdraw consent.</strong> Twilio provides STOP handling for the long-code SMS number used in this pilot.</P>
        <P>You may also email <a href="mailto:founders@sidira.ai" style={{ color: TOKENS.ink }}>founders@sidira.ai</a> to request that testing messages stop or to report an opt-out problem.</P>
      </PolicySection>

      <PolicySection title="HELP and support">
        <P><strong>Reply HELP for help.</strong> For support with Monsi, email <a href="mailto:founders@sidira.ai" style={{ color: TOKENS.ink }}>founders@sidira.ai</a>.</P>
      </PolicySection>

      <PolicySection title="Test limitations">
        <P>Monsi is an experimental test service. Replies may be limited, delayed, incorrect, or unavailable. Do not rely on Monsi for urgent or important decisions.</P>
        <P><strong>Monsi is not an emergency service.</strong> Contact the appropriate emergency services directly when needed.</P>
      </PolicySection>

      <PolicySection title="Privacy">
        <P>Read the <Link href="/monsi/privacy" style={{ color: TOKENS.ink }}>Monsi SMS Privacy Policy</Link> for information about phone numbers, message text, delivery metadata, Twilio processing and retention, and privacy requests.</P>
      </PolicySection>

      <PolicySection title="Changes to the pilot">
        <P>These terms describe the current private scripted SMS pilot. We will update them before introducing AI processing, separate application message storage, or customer use. Updates will be published here with a revised effective date.</P>
      </PolicySection>
    </PolicyDocument>
  );
}
