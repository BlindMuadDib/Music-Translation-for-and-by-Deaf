import pygame

def display_lyrics(audio_file, synchronized_transcript):
    """Display lyrics line by line synchronized with audio using pygame"""
    pygame.init()
    screen = pygame.display.set_mode((800, 400))
    pygame.display.set_caption("Sing-Along Lyrics")
    font = pygame.font.Font(None, 36)

    # Load and play audio
    pygame.mixer.init()
    pygame.mixer.music.load(audio_file)
    pygame.mixer.music.play()

    # Initialize colors
    white = (255, 255, 255)
    black = (0, 0, 0)

    current_line_index = 0
    displayed_line = None # Keep track of the currently displayed text

    running = True
    while running:
        current_audio_time = pygame.mixer.music.get_pos() / 1000 # Get current time in seconds

        if current_line_index < len(synchronized_transcript):
            line = synchronized_transcript[current_line_index]
            line_text = " ".join(word[2] for word in line)

            # Get the timing for the current line
            line_start_time = max(line[0][0] - 0.5, 0) # Start slightly before the first word
            next_line_start_time = (
                synchronized_transcript[current_line_index + 1][0][0]
                if current_line_index + 1 < len(synchronized_transcript)
                else None
            )
            current_line_end_time = line[-1][1]

            # Handles gaps of 5 seconds or more
            if next_line_start_time and next_line_start_time - current_line_end_time >= 5:
                if current_audio_time >= current_line_end_time + 3: # Show "...instrumental..."
                    if displayed_line != "...instrtumental...":
                        screen.fill(white)
                        text_surface = font.render("...instrumental...", True, black)
                        text_rect = text_surface.get_rect(center=(400, 200))
                        screen.blit(text_surface, text_rect)
                        pygame.display.flip()
                        displayed_line = "...instrumental..."

                    # Transition to the next line when it's time
                    if current_audio_time >= line_start_time:
                        if displayed_line != line_text:
                            current_line_index += 1
                            displayed_line = None
                continue

            # Display current line when appropriate
            if current_audio_time >= line_start_time:
                if displayed_line != line_text: # Avoid redundant rendering
                    screen.fill(white)
                    text_surface = font.render(line_text, True, black)
                    text_rect = text_surface.get_rect(center=(400, 200))
                    screen.blit(text_surface, text_rect)
                    pygame.display.flip()
                    displayed_line = line_text

                # Transition to the next line only if there's no large gap
                if next_line_start_time and current_audio_time >= next_line_start_time - 0.5:
                    current_line_index += 1
                    displayed_line = None

        else:
            # Stop updating when lyrics are finished
            running = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

    pygame.quit()