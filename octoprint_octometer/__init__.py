import os
import sqlite3
import time

import octoprint.events
import octoprint.filemanager
import octoprint.filemanager.util
import octoprint.plugin

import datetime.timedelta


class OctometerPlugin(
    octoprint.plugin.EventHandlerPlugin, octoprint.plugin.StartupPlugin
):
    def create_connection(self):
        self.conn = None
        self.conn = sqlite3.connect(self.db_path)
        self.c = self.conn.cursor()

    def on_after_startup(self):
        self._logger.info("Hello world!")
        self.db_file = "octometer.db"
        plugin_path = os.path.realpath(__file__)
        file_dir = os.path.dirname(plugin_path)
        self.db_path = os.path.join(file_dir, self.db_file)

        try:
            self.conn = self.create_connection()
        except sqlite3.Error as e:
            self._logger.info(
                f"Could not connect to DB at {self.db_path}, failed with error {e}."
            )
            with open(self.db_file, "w") as f:
                pass

            self.create_connection()
        finally:
            if self.conn:
                self.c.execute(
                    """CREATE TABLE IF NOT EXISTS prints (  end_time TEXT PRIMARY KEY,
                                                            file_name TEXT NOT NULL,
                                                            outcome TEXT,
                                                            duration TEXT NOT NULL,
                                                            filament_used TEXT NOT NULL) """
                )
                self.c.commit()
                self.conn.close()

    def on_event(self, event, payload):
        if event == octoprint.events.Events.PRINT_DONE:
            end_time = time.time()
            duration = payload["time"]
            file_name = payload["name"]
            outcome = "success"
            metadata = self._file_manager.get_metadata(
                payload["origin"], payload["path"]
            )
            filament_total = sum(
                [
                    metadata["analysis"]["filament"][tool]["length"]
                    for tool in metadata["analysis"]["filament"]
                ]
            )
            filament_used = filament_total

            self_logger.info(
                f"Print {file_name} finished after {str(datetime.timedelta(seconds=duration))}, writing to database..."
            )

            self.create_connection()
            self.c.execute(
                """INSERT INTO prints VALUES(?,?,?,?,?)""",
                end_time,
                file_name,
                outcome,
                duration,
                filament_used,
            )
            self.c.commit()
            self.conn.close()

            self._logger.info(f"Written print details to {self.db_path}.")
        elif (
            event == octoprint.events.Events.PRINT_CANCELLED
            or event == octoprint.events.Events.ERROR
        ):
            end_time = time.time()
            duration = payload["time"]
            file_name = payload["name"]
            outcome = payload["reason"]
            metadata = self._file_manager.get_metadata(
                payload["origin"], payload["path"]
            )
            try:
                print_time = metadata["statistics"]["averagePrintTime"]["_default"]
            except KeyError:
                print_time = metadata["analysis"]["estimatedPrintTime"]

            percent_done = duration / print_time
            filament_total = sum(
                [
                    metadata["analysis"]["filament"][tool]["length"]
                    for tool in metadata["analysis"]["filament"]
                ]
            )
            filament_used = filament_total * percent_done

            self_logger.info(
                f"Print {file_name} {outcome} after {str(datetime.timedelta(seconds=duration))}, writing to database..."
            )

            self.create_connection()
            self.c.execute(
                """INSERT INTO prints VALUES(?,?,?,?,?)""",
                end_time,
                file_name,
                outcome,
                duration,
                filament_used,
            )
            self.c.commit()
            self.conn.close()

            self._logger.info(f"Written print details to {self.db_path}.")


__plugin_pythoncompat__ = ">=3.7, <4"
__plugin_implementation__ = OctometerPlugin()
