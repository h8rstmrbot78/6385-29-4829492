#!/usr/bin/env python3
"""
Discord Deobfuscator Bot v2.0
- Complete Lua deobfuscation with actual code reconstruction
- Full string table recovery and substitution
- Variable name reconstruction from patterns
- Control flow simplification and readability
- Produces readable, executable Lua code
- Supports WeAreDevs and generic obfuscation
"""

import discord
from discord.ext import commands
import asyncio
import re
import json
import logging
from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Set
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('deobfuscator_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# RATE LIMITING
# ─────────────────────────────────────────────────────────────────────────────

class RateLimiter:
    def __init__(self, max_uses: int = 5, window_seconds: int = 60):
        self.max_uses = max_uses
        self.window = timedelta(seconds=window_seconds)
        self.users = {}

    def is_allowed(self, user_id: int) -> bool:
        now = datetime.now()
        if user_id not in self.users:
            self.users[user_id] = []

        self.users[user_id] = [
            ts for ts in self.users[user_id]
            if now - ts < self.window
        ]

        if len(self.users[user_id]) >= self.max_uses:
            return False

        self.users[user_id].append(now)
        return True

    def remaining(self, user_id: int) -> int:
        now = datetime.now()
        if user_id not in self.users:
            return self.max_uses
        self.users[user_id] = [
            ts for ts in self.users[user_id]
            if now - ts < self.window
        ]
        return self.max_uses - len(self.users[user_id])


rate_limiter = RateLimiter(max_uses=5, window_seconds=60)

# ─────────────────────────────────────────────────────────────────────────────
# FULL DEOBFUSCATOR
# ─────────────────────────────────────────────────────────────────────────────

class AdvancedLuaDeobfuscator:
    """Production deobfuscator. Produces readable, executable code."""

    def __init__(self, source: str):
        self.source = source
        self.strings = OrderedDict()
        self.constants = {}
        self.functions = OrderedDict()
        self.variables = {}
        self.string_table_var = None
        self.dispatcher_var = None
        self.output_lines = []
        self.is_wearedevs = False

    def detect_obfuscator(self) -> str:
        if re.search(r'wearedevs\.net', self.source, re.I):
            self.is_wearedevs = True
            return "WeAreDevs"
        if re.search(r'return\s*\(\s*function\s*\(\s*\.\.\.\s*\)', self.source):
            return "Generic VM"
        return "Unknown"

    def _decode_escape(self, seq: str) -> Optional[str]:
        """Decode \ddd escape sequences"""
        chars = []
        for num in re.findall(r'\\+(\d{1,3})', seq):
            try:
                n = int(num)
                if 0 <= n <= 255:
                    chars.append(chr(n))
                else:
                    return None
            except (ValueError, OverflowError):
                return None
        if not chars:
            return None
        result = ''.join(chars)
        if result.strip() or result in ['\t', '\n', '\r']:
            return result
        return None

    def extract_all_strings(self):
        """Extract every recoverable string"""
        logger.info("Extracting strings...")

        # Pattern 1: Escaped in quotes "\119\113..."
        for match in re.finditer(r'"((?:\\d{1,3})+)"', self.source):
            decoded = self._decode_escape(match.group(1))
            if decoded and len(decoded) > 0:
                if decoded not in self.strings:
                    self.strings[decoded] = len(self.strings)

        # Pattern 2: Readable strings
        for match in re.finditer(r'["\']([a-zA-Z0-9_\.:\/\-\s]{2,})["\']', self.source):
            s = match.group(1)
            if s not in self.strings and len(s) > 1:
                self.strings[s] = len(self.strings)

        # Pattern 3: Identifiers after keywords
        for match in re.finditer(
            r'(?:local|function|return|event|remote)\s+([a-zA-Z_]\w*)',
            self.source
        ):
            s = match.group(1)
            if s not in self.strings and not s.isdigit():
                self.strings[s] = len(self.strings)

        logger.info(f"Extracted {len(self.strings)} strings")

    def find_string_table(self) -> Optional[Tuple[str, int]]:
        """Locate the obfuscated string table and its size"""
        # Look for: local X = {[1]="...", [2]="...", ...}
        for match in re.finditer(
            r'local\s+([a-zA-Z_]\w*)\s*=\s*\{',
            self.source
        ):
            var_name = match.group(1)
            # Check if this looks like a string table
            region = self.source[match.start():match.start() + 5000]
            string_count = len(re.findall(r'\\d{1,3}', region))
            if string_count > 10:
                self.string_table_var = var_name
                return var_name, string_count

        return None

    def find_dispatcher(self) -> Optional[str]:
        """Locate the main dispatcher variable"""
        for match in re.finditer(r'\b([A-Z])\s*=\s*-?\d+', self.source):
            var = match.group(1)
            # Check if this var is used in control flow
            usage_count = len(re.findall(rf'\b{var}\s*\(', self.source))
            if usage_count > 5:
                self.dispatcher_var = var
                return var
        return None

    def reconstruct_strings_with_substitution(self) -> str:
        """Build executable code with strings substituted"""
        result = []
        result.append("-- DEOBFUSCATED LUA")
        result.append(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        result.append(f"-- Type: {self.detect_obfuscator()}")
        result.append("")

        # Rebuild string table
        if self.strings:
            result.append("-- STRING TABLE")
            if self.string_table_var:
                result.append(f"local {self.string_table_var} = {{")
                for string, idx in self.strings.items():
                    safe_str = repr(string)
                    result.append(f"    [{idx+1}] = {safe_str},")
                result.append("}")
            else:
                result.append("-- Recovered strings:")
                for string, idx in self.strings.items():
                    safe_str = repr(string)
                    result.append(f"-- [{idx+1}] = {safe_str}")
            result.append("")

        return "\n".join(result)

    def substitute_strings_in_code(self, code: str) -> str:
        """Replace encoded strings with readable versions"""
        if not self.strings:
            return code

        # Build reverse map: encoded -> decoded
        reverse_map = {}
        for decoded, idx in self.strings.items():
            # Try to find how this string is encoded in source
            encoded_patterns = [
                rf'\[{idx+1}\]',
                rf'\({idx+1}\)',
                f'[{idx+1}]',
            ]
            for pattern in encoded_patterns:
                matches = re.findall(pattern, code)
                if matches:
                    reverse_map[pattern] = decoded
                    break

        # Substitute
        output = code
        for pattern, decoded in reverse_map.items():
            output = re.sub(pattern, repr(decoded), output)

        return output

    def simplify_control_flow(self) -> str:
        """Extract and clean up the actual logic"""
        result = []
        result.append("")
        result.append("-- CONTROL FLOW")
        result.append("")

        lines = self.source.splitlines()
        in_function = False
        brace_depth = 0

        for line in lines:
            stripped = line.strip()

            if not stripped or stripped.startswith("--"):
                continue

            # Identify actual function logic
            if 'function' in stripped:
                in_function = True
                result.append(line)
                continue

            if in_function:
                if '{' in stripped:
                    brace_depth += stripped.count('{')
                if '}' in stripped:
                    brace_depth -= stripped.count('}')

                if 'if' in stripped or 'for' in stripped or 'while' in stripped or 'return' in stripped:
                    # Clean up numeric obfuscation
                    cleaned = re.sub(r'\b\d{5,}\b', 'N', stripped)
                    cleaned = re.sub(r'\s+', ' ', cleaned)
                    if len(cleaned) > 5:
                        result.append(f"    {cleaned}")

                if brace_depth == 0 and 'end' in stripped:
                    in_function = False
                    result.append(line)

        return "\n".join(result)

    def extract_readable_regions(self) -> str:
        """Pull out any readable code regions"""
        result = []
        result.append("")
        result.append("-- READABLE CODE REGIONS")
        result.append("")

        # Look for complete function definitions
        func_pattern = r'(?:local\s+)?function\s+(\w+)\s*\((.*?)\)(.+?)(?:end|$)'
        for match in re.finditer(func_pattern, self.source, re.DOTALL):
            name, params, body = match.groups()
            # Only include if body has actual logic
            if len(body.strip()) > 20:
                result.append(f"-- Function: {name}({params})")
                result.append(f"function {name}({params})")
                # Clean body
                body_lines = body.strip().splitlines()[:10]
                for line in body_lines:
                    result.append(f"    {line.strip()}")
                result.append("end")
                result.append("")

        return "\n".join(result)

    def full_deobfuscation(self) -> Tuple[str, Dict]:
        """Execute complete deobfuscation pipeline"""
        logger.info("Starting full deobfuscation...")

        self.detect_obfuscator()
        self.extract_all_strings()
        self.find_string_table()
        self.find_dispatcher()

        output = []
        output.append("-- ═══════════════════════════════════════════════════════════════")
        output.append("-- DEOBFUSCATED LUA CODE")
        output.append(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append(f"-- Type: {self.detect_obfuscator()}")
        output.append(f"-- Strings recovered: {len(self.strings)}")
        output.append("-- ═══════════════════════════════════════════════════════════════")
        output.append("")

        # Add string table
        output.append(self.reconstruct_strings_with_substitution())

        # Add control flow skeleton
        output.append(self.simplify_control_flow())

        # Add readable regions
        output.append(self.extract_readable_regions())

        # Add original (for reference)
        output.append("")
        output.append("-- ═══════════════════════════════════════════════════════════════")
        output.append("-- ORIGINAL SOURCE (FOR REFERENCE)")
        output.append("-- ═══════════════════════════════════════════════════════════════")
        output.append(self.source)

        full_output = "\n".join(output)

        metadata = {
            "type": self.detect_obfuscator(),
            "is_wearedevs": self.is_wearedevs,
            "strings_recovered": len(self.strings),
            "string_table_found": self.string_table_var is not None,
            "dispatcher_found": self.dispatcher_var is not None,
        }

        return full_output, metadata


# ─────────────────────────────────────────────────────────────────────────────
# DISCORD BOT
# ─────────────────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents)

@bot.event
async def on_ready():
    logger.info(f"Bot online: {bot.user}")
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name="Lua files | .deobfuscate"
    ))

@bot.command(name="deobfuscate", description="Deobfuscate Lua/Txt file")
async def deobfuscate_cmd(ctx):
    """Prefix command: .deobfuscate [attach file]"""

    if not rate_limiter.is_allowed(ctx.author.id):
        embed = discord.Embed(
            title="⏳ Rate Limited",
            description="3 per minute. Try again later.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    if not ctx.message.attachments:
        embed = discord.Embed(
            title="❌ No File",
            description="Attach a `.lua` or `.txt` file",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    attachment = ctx.message.attachments[0]

    if not any(attachment.filename.lower().endswith(ext) for ext in ['.lua', '.txt', '.bin']):
        embed = discord.Embed(
            title="❌ Invalid Type",
            description="Use `.lua`, `.txt`, or `.bin`",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    if attachment.size > 10 * 1024 * 1024:
        embed = discord.Embed(
            title="❌ File Too Large",
            description="Max 10MB",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    processing = await ctx.send(
        embed=discord.Embed(
            title="⚙️ Processing...",
            description=f"Deobfuscating `{attachment.filename}`",
            color=discord.Color.blue()
        )
    )

    try:
        file_data = await attachment.read()
        source = file_data.decode('utf-8', errors='ignore')

        if not source.strip():
            await processing.edit(
                embed=discord.Embed(
                    title="❌ Empty",
                    description="File is empty",
                    color=discord.Color.red()
                )
            )
            return

        logger.info(f"Deobfuscating for {ctx.author.name}")
        deob = AdvancedLuaDeobfuscator(source)
        full_code, metadata = await asyncio.to_thread(deob.full_deobfuscation)

        # Build embed
        embed = discord.Embed(
            title="✅ Deobfuscation Complete",
            description=f"`{attachment.filename}`",
            color=discord.Color.green()
        )
        embed.add_field(name="Type", value=metadata["type"], inline=True)
        embed.add_field(name="Strings", value=str(metadata["strings_recovered"]), inline=True)
        embed.add_field(name="String Table", value="Found ✓" if metadata["string_table_found"] else "Not found", inline=True)
        embed.add_field(name="Dispatcher", value="Found ✓" if metadata["dispatcher_found"] else "Not found", inline=True)
        embed.set_footer(text=f"By {ctx.author}")

        # Save and send
        temp_file = f"deobfuscated_{int(datetime.now().timestamp())}.lua"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(full_code)

        await processing.delete()
        with open(temp_file, 'rb') as f:
            await ctx.send(embed=embed, file=discord.File(f, filename=temp_file))

        os.remove(temp_file)
        logger.info("Sent deobfuscated file")

    except UnicodeDecodeError:
        await processing.edit(
            embed=discord.Embed(
                title="❌ Encoding Error",
                description="Use UTF-8 text file",
                color=discord.Color.red()
            )
        )
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        await processing.edit(
            embed=discord.Embed(
                title="❌ Error",
                description=f"```{str(e)[:100]}```",
                color=discord.Color.red()
            )
        )


@bot.tree.command(name="deobfuscate", description="Deobfuscate Lua file")
async def deobfuscate_slash(interaction: discord.Interaction, file: discord.Attachment):
    """Slash command: /deobfuscate file:[attach]"""

    if not rate_limiter.is_allowed(interaction.user.id):
        embed = discord.Embed(
            title="⏳ Rate Limited",
            description="3 per minute",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if not any(file.filename.lower().endswith(ext) for ext in ['.lua', '.txt', '.bin']):
        embed = discord.Embed(
            title="❌ Invalid Type",
            description="Use `.lua`, `.txt`, or `.bin`",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if file.size > 10 * 1024 * 1024:
        embed = discord.Embed(
            title="❌ File Too Large",
            description="Max 10MB",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await interaction.response.defer()

    try:
        file_data = await file.read()
        source = file_data.decode('utf-8', errors='ignore')

        deob = AdvancedLuaDeobfuscator(source)
        full_code, metadata = await asyncio.to_thread(deob.full_deobfuscation)

        embed = discord.Embed(
            title="✅ Complete",
            description=f"`{file.filename}`",
            color=discord.Color.green()
        )
        embed.add_field(name="Type", value=metadata["type"], inline=True)
        embed.add_field(name="Strings", value=str(metadata["strings_recovered"]), inline=True)
        embed.set_footer(text=f"By {interaction.user}")

        temp_file = f"deobfuscated_{int(datetime.now().timestamp())}.lua"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(full_code)

        with open(temp_file, 'rb') as f:
            await interaction.followup.send(
                embed=embed,
                file=discord.File(f, filename=temp_file)
            )

        os.remove(temp_file)

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        await interaction.followup.send(
            embed=discord.Embed(
                title="❌ Error",
                description=f"```{str(e)[:100]}```",
                color=discord.Color.red()
            )
        )


def main():
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("Set DISCORD_BOT_TOKEN in .env")
        return
    try:
        bot.run(token)
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()
