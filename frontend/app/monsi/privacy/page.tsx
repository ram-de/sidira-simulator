import type { Metadata } from "next";
import Link from "next/link";

import { PolicyDocument, PolicyParagraph as P, PolicySection } from "../PolicyDocument";
import { TOKENS } from "@/lib/design";

export const metadata: Metadata = {
  title: "Monsi SMS Privacy Policy — Sidira",
  description: "Privacy practices for Monsi’s private SMS pilot, including message data, Twilio processing, retention, and messaging choices.",
  alternates: { canonical: "https://sidira.ai/monsi/privacy" },
};

export default function MonsiPrivacyPage() {
  return (
    <PolicyDocument title="Monsi SMS Privacy Policy" current="privacy">
      <PolicySection title="What this policy covers">
        <P>Monsi is a personal assistant proof of concept being tested through SMS. The private pilot is limited to invited adult testers and does not involve customers.</P>
        <P>The current test sends basic greetings and scripted conversational replies. It does not send marketing messages or verification codes. Questions about Monsi or this policy can be sent to <a href="mailto:founders@sidira.ai" style={{ color: TOKENS.ink }}>founders@sidira.ai</a>.</P>
      </PolicySection>

      <PolicySection title="Information used in the test">
        <P>The SMS test involves participant and sender phone numbers, incoming and outgoing message text, and delivery metadata such as message identifiers, timestamps, delivery status, and error information.</P>
        <P>This information is used to send and receive test messages, test scripted replies, and investigate delivery or response problems. The operator may access Twilio message logs for these testing purposes.</P>
      </PolicySection>

      <PolicySection title="Service providers and sharing">
        <P>Twilio processes phone numbers, message content, and delivery metadata to deliver the SMS messages. Mobile carriers also handle messages as part of SMS delivery.</P>
        <P>No AI provider processes message content in the current transport test. Replies are scripted.</P>
        <P>Monsi does not sell participants’ personal information or share phone numbers, message content, mobile opt-in information, or consent with third parties for their own marketing or promotional purposes. This restriction does not prevent the service-provider processing needed to deliver and test the SMS program.</P>
      </PolicySection>

      <PolicySection title="Retention and privacy requests">
        <P>The current Monsi application does not separately persist SMS messages. Twilio processes and may store message content and delivery metadata under the account’s retention settings and Twilio’s applicable practices. Retention can depend on those settings and provider practices; this policy does not specify a fixed retention period.</P>
        <P>For privacy questions or a deletion request, email <a href="mailto:founders@sidira.ai" style={{ color: TOKENS.ink }}>founders@sidira.ai</a>. Requests are handled individually, subject to the records available and provider capabilities. An automated deletion process is not currently implemented, and removing application records would not necessarily remove provider records.</P>
        <P>Please avoid sending sensitive personal information during this SMS test.</P>
      </PolicySection>

      <PolicySection title="Consent, choices, and support">
        <P>Consent is obtained directly from each tester before their number is included in the pilot. Participation is voluntary. Reply STOP to withdraw consent and stop Monsi SMS messages, or contact <a href="mailto:founders@sidira.ai" style={{ color: TOKENS.ink }}>founders@sidira.ai</a> for support.</P>
        <P>See the <Link href="/monsi/terms" style={{ color: TOKENS.ink }}>Monsi SMS Terms</Link> for message frequency, possible carrier charges, and help information.</P>
      </PolicySection>

      <PolicySection title="Changes to the pilot">
        <P>This policy describes the current private scripted SMS pilot. We will update it before introducing AI processing, separate application message storage, or customer use. Updates will be published here with a revised effective date.</P>
      </PolicySection>
    </PolicyDocument>
  );
}
