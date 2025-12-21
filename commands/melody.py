from logging import PlaceHolder
import discord
from discord import app_commands, ui
import wavesynth as ws
import tempfile
import os


def generate_melody(mode: str, data: str):
    NOTE_LENGTH = 0.4

    def parse_notes(s):
        notes = []
        durations = []
        
        if ',' in s:
            entries = s.split(',')
            for entry in entries:
                parts = entry.strip().split()
                if len(parts) >= 1:
                    note = parts[0]
                    duration = float(parts[1]) if len(parts) >= 2 else NOTE_LENGTH
                    
                    normalized_note = note[0].upper()
                    if len(note) > 1:
                        if note[1] == '#':
                            normalized_note += 's' + note[2:]
                        elif note[1].lower() == 's':
                            normalized_note += 's' + note[2:]
                        elif note[1].lower() == 'b':
                            normalized_note += 'b' + note[2:]
                        else:
                            normalized_note += note[1:]
                    
                    notes.append(normalized_note)
                    durations.append(duration)
            return notes, durations
        else:
            for note in s.split():
                if not note:
                    continue
                normalized_note = note[0].upper()
                if len(note) > 1:
                    if note[1] == '#':
                        normalized_note += 's' + note[2:]
                    elif note[1].lower() == 's':
                        normalized_note += 's' + note[2:]
                    elif note[1].lower() == 'b':
                        normalized_note += 'b' + note[2:]
                    else:
                        normalized_note += note[1:]
                notes.append(normalized_note)
                durations.append(NOTE_LENGTH)
            return notes, durations

    def parse_beats(s):
        mapping = {"_": 0.6, ".": 0.2, "-": 0.4}
        return [mapping.get(ch, 0.4) for ch in s]

    ws.resetTracks()
    ws.setInstrument(ws.keyboard)
    ws.setVolume(0.6)
        
    if mode == "notes":
        notes, durations = parse_notes(data)
    else:
        durations = parse_beats(data)
        notes = ["A4"] * len(durations)

    for n, d in zip(notes, durations):
        try:
            pitch_const = getattr(ws, n.replace('#', 's'))
            ws.setPitch(pitch_const)
            ws.addNote(d)
        except (AttributeError, ValueError):
            ws.setPitch(ws.A4)
            ws.addNote(d)

    # Save to temporary file and read into memory
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        ws.saveTrack(tmp_path)
        with open(tmp_path, 'rb') as f:
            audio_data = f.read()
        return audio_data
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


class MelodyInputModal(ui.Modal):
    def __init__(self, mode, callback):
        super().__init__(title="Enter Your Melody")

        if mode == "notes":
            placeholder = "e.g., C4 E4 G4 or E4 1.0 or G4 0.5, C5 1.5"
        else:
            placeholder = "e.g., _.-_.."

        self.data_input = ui.TextInput(
            label="Notes or Beat Pattern",
            placeholder=placeholder,
            required=True,
            min_length=1,
            max_length=1000,
        )

        self.add_item(self.data_input)
        self.mode = mode
        self.callback = callback

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback(interaction, self.mode, self.data_input.value)


class MelodyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.mode = None

    @discord.ui.button(label="Notes Mode", style=discord.ButtonStyle.primary)
    async def notes_mode(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.mode = "notes"
        await interaction.response.send_modal(
            MelodyInputModal(self.mode, self.on_modal_submit)
        )
        self.stop()

    @discord.ui.button(label="Beats Mode", style=discord.ButtonStyle.secondary)
    async def beats_mode(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.mode = "beats"
        await interaction.response.send_modal(
            MelodyInputModal(self.mode, self.on_modal_submit)
        )
        self.stop()

    async def on_modal_submit(self, interaction: discord.Interaction, mode, data):
        await interaction.response.defer()
        try:
            wav_bytes = generate_melody(mode, data)
            import io
            wav_file = io.BytesIO(wav_bytes)
            file = discord.File(wav_file, filename="melody.wav")
            await interaction.followup.send("Here's your melody!", file=file)
        except Exception as e:
            await interaction.followup.send(f"Oops! Something went wrong: {e}", ephemeral=True)


async def melody_setup(bot):
    @bot.tree.command(name="melody", description="Create a simple melody!")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def melody(interaction: discord.Interaction):
        view = MelodyView()
        await interaction.response.send_message(
            "Let's make a melody!\nChoose an input mode:",
            view=view,
            ephemeral=True,
        )
