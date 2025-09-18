import React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

interface ColorSwatchProps {
  name: string;
  color: string;
  value: string;
  description?: string;
}

function ColorSwatch({ name, color, value, description }: ColorSwatchProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{name}</span>
        <Badge variant="outline" className="text-xs">{value}</Badge>
      </div>
      <div 
        className="w-full h-12 rounded-lg border shadow-sm"
        style={{ backgroundColor: color }}
      />
      {description && (
        <p className="text-xs text-muted-foreground">{description}</p>
      )}
    </div>
  );
}

export function RadixColorsShowcase() {
  const colorPalettes = [
    {
      name: "Primary Blue",
      colors: [
        { name: "Blue 50", value: "#eff6ff", description: "Lightest background" },
        { name: "Blue 100", value: "#dbeafe", description: "Subtle background" },
        { name: "Blue 200", value: "#bfdbfe", description: "Border/subtle" },
        { name: "Blue 300", value: "#93c5fd", description: "Border" },
        { name: "Blue 400", value: "#60a5fa", description: "Muted text" },
        { name: "Blue 500", value: "#3b82f6", description: "Primary brand" },
        { name: "Blue 600", value: "#2563eb", description: "Primary hover" },
        { name: "Blue 700", value: "#1d4ed8", description: "Primary active" },
        { name: "Blue 800", value: "#1e40af", description: "Text" },
        { name: "Blue 900", value: "#1e3a8a", description: "Dark text" },
        { name: "Blue 950", value: "#172554", description: "Darkest text" },
      ]
    },
    {
      name: "AI Purple",
      colors: [
        { name: "Purple 50", value: "#faf5ff", description: "Lightest background" },
        { name: "Purple 100", value: "#f3e8ff", description: "Subtle background" },
        { name: "Purple 200", value: "#e9d5ff", description: "Border/subtle" },
        { name: "Purple 300", value: "#ddd6fe", description: "Border" },
        { name: "Purple 400", value: "#c4b5fd", description: "Muted text" },
        { name: "Purple 500", value: "#8b5cf6", description: "AI/Automation" },
        { name: "Purple 600", value: "#7c3aed", description: "AI hover" },
        { name: "Purple 700", value: "#6d28d9", description: "AI active" },
        { name: "Purple 800", value: "#5b21b6", description: "Text" },
        { name: "Purple 900", value: "#4c1d95", description: "Dark text" },
        { name: "Purple 950", value: "#2e1065", description: "Darkest text" },
      ]
    },
    {
      name: "Brand Colors",
      colors: [
        { name: "Primary", value: "#3b82f6", description: "Main brand blue" },
        { name: "Secondary", value: "#8b5cf6", description: "AI/automation purple" },
        { name: "Success", value: "#22c55e", description: "Positive metrics" },
        { name: "Warning", value: "#f97316", description: "Alerts" },
        { name: "Error", value: "#ef4444", description: "Critical alerts" },
      ]
    }
  ];

  return (
    <div className="space-y-8 p-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Custom Radix Colors</h1>
        <p className="text-muted-foreground">
          Fikiri Solutions custom color palette built with Radix Colors
        </p>
      </div>

      {colorPalettes.map((palette) => (
        <Card key={palette.name}>
          <CardHeader>
            <CardTitle>{palette.name}</CardTitle>
            <CardDescription>
              {palette.name === "Brand Colors" 
                ? "Core brand colors for Fikiri Solutions"
                : `Complete ${palette.name.toLowerCase()} color scale`
              }
            </CardDescription>
          </CardHeader>
          <Separator />
          <CardContent className="pt-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {palette.colors.map((color) => (
                <ColorSwatch
                  key={color.name}
                  name={color.name}
                  color={color.value}
                  value={color.value}
                  description={color.description}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      ))}

      <Card>
        <CardHeader>
          <CardTitle>Usage Examples</CardTitle>
          <CardDescription>
            How to use these colors in your components
          </CardDescription>
        </CardHeader>
        <Separator />
        <CardContent className="pt-6 space-y-4">
          <div className="space-y-2">
            <h4 className="font-medium">Tailwind Classes</h4>
            <div className="bg-muted p-4 rounded-lg">
              <code className="text-sm">
                bg-primary text-primary-foreground<br/>
                bg-secondary text-secondary-foreground<br/>
                bg-brand-primary bg-brand-secondary<br/>
                text-blue-500 text-purple-500
              </code>
            </div>
          </div>
          
          <div className="space-y-2">
            <h4 className="font-medium">CSS Variables</h4>
            <div className="bg-muted p-4 rounded-lg">
              <code className="text-sm">
                hsl(var(--primary))<br/>
                hsl(var(--secondary))<br/>
                hsl(var(--brand-primary))
              </code>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
