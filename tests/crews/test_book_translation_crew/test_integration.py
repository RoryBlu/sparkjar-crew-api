"""Integration tests for Book Translation Crew with focus on translation quality."""
import pytest
import asyncio
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from src.crews.book_translation_crew.main import kickoff
from database.connection import get_db_session
from database.models import ClientUsers, ClientSecrets


class TestBookTranslationIntegration:
    """Integration tests with real database and 5-page sample."""
    
    @pytest.fixture
    async def test_client_data(self):
        """Setup test client and database connection."""
        # This would use test database in real scenario
        return {
            "client_user_id": "3a411a30-1653-4caf-acee-de257ff50e36",
            "client_id": "gvfiezbiyfggwdlvqnsc",
            "book_key": "test_translation_quality",
            "database_url": None  # Will be fetched from secrets
        }
    
    @pytest.fixture
    async def sample_spanish_pages(self):
        """5 sample pages in Spanish for quality testing."""
        return [
            {
                "page_number": 1,
                "page_text": """EL BARÓN RAMPANTE

                Capítulo 1

                Fue el 15 de junio de 1767 cuando Cosimo Piovasco di Rondò, mi hermano, se sentó con nosotros por última vez. Recuerdo como si fuera ayer: estábamos en el comedor de nuestra villa de Ombrosa, las ventanas enmarcaban las copas de las grandes encinas del parque. Cosimo dijo: "No quiero y no comeré nunca más caracoles." Mi padre, el barón Arminio Piovasco di Rondò, estalló: "¡Comerás lo que te pongan en la mesa!" Pero Cosimo se mantuvo firme en su decisión.""",
                "file_name": "page_1.txt",
                "language_code": "es"
            },
            {
                "page_number": 2,
                "page_text": """Era mediodía, y nuestra familia estaba reunida alrededor de la mesa: mi padre, mi madre la baronesa Corradina, mi hermana Battista y el abate Fauchelafleur, que era nuestro preceptor y administrador de la casa. Al final de la mesa, Cosimo y yo nos sentábamos en silencio. Yo tenía ocho años y mi hermano doce; yo siempre comprendí que él estaba destinado a hacer cosas extraordinarias.

                La discusión sobre los caracoles continuó. Mi madre intentó mediar: "Cosimo, hijo, los caracoles son nutritivos y deliciosos." Pero mi hermano ya había tomado su decisión. Se levantó de la mesa, salió al jardín y trepó a una encina. "¡No bajaré nunca más!" gritó desde las ramas.""",
                "file_name": "page_2.txt",
                "language_code": "es"
            },
            {
                "page_number": 3,
                "page_text": """Desde ese día, Cosimo vivió en los árboles. Al principio pensamos que era un capricho infantil, que el hambre y el cansancio lo harían bajar. Pero pasaron los días, las semanas, los meses, y mi hermano seguía arriba. Había construido refugios entre las ramas, aprendido a moverse de árbol en árbol sin tocar el suelo, y desarrollado toda una nueva forma de vida.

                Mi padre estaba furioso. "¡Un Piovasco di Rondò viviendo como un mono!" gritaba. Pero también había en su voz un dejo de admiración por la determinación de su hijo. Mi madre lloraba en silencio, mientras Battista se burlaba: "¡Ahí está nuestro hermano el pájaro!"

                Yo era el único que lo visitaba regularmente, subiéndome a las ramas bajas para conversar con él.""",
                "file_name": "page_3.txt",
                "language_code": "es"
            },
            {
                "page_number": 4,
                "page_text": """La vida de Cosimo en los árboles no era solitaria. Pronto conoció a Viola, la hija de los Ondariva, nuestros vecinos. Ella también era rebelde y aventurera, y no le importaba trepar a los árboles para estar con él. Su amistad se convirtió en amor, aunque era un amor complicado por las circunstancias extraordinarias.

                Cosimo también hizo amistad con los carboneros, los cazadores furtivos y los bandidos que vivían en el bosque. Ellos lo respetaban y lo llamaban "El Barón de los Árboles". Mi hermano les enseñaba a leer y escribir, y ellos le enseñaban los secretos del bosque.

                Desde las copas de los árboles, Cosimo podía ver todo Ombrosa: las intrigas de los nobles, los amores secretos, las conspiraciones políticas. Se convirtió en una especie de vigilante benévolo de nuestro pequeño mundo.""",
                "file_name": "page_4.txt",
                "language_code": "es"
            },
            {
                "page_number": 5,
                "page_text": """Con el tiempo, la fama de mi hermano se extendió más allá de Ombrosa. Viajeros ilustres venían a verlo: filósofos, naturalistas, poetas. Cosimo discutía con ellos sobre las ideas de la Ilustración, sobre Rousseau y Voltaire, siempre desde su reino arbóreo. Había instalado una biblioteca entre las ramas, con poleas para subir los libros.

                Incluso participó en batallas, disparando desde los árboles contra los invasores austriacos. Los generales lo consultaban sobre estrategia, pues desde su altura podía ver los movimientos del enemigo. Se convirtió en héroe local, el noble que había renunciado a los privilegios terrenales pero no a sus deberes.

                Yo, mientras tanto, había heredado el título y las responsabilidades. Pero siempre envidiaba la libertad de mi hermano, su mundo sin límites entre las hojas y el cielo.""",
                "file_name": "page_5.txt",
                "language_code": "es"
            }
        ]
    
    async def setup_test_data(self, test_client_data, sample_pages):
        """Insert test pages into the database."""
        async with get_db_session() as session:
            # Get client database URL
            result = await session.execute(
                text("""
                    SELECT cs.secret_value 
                    FROM client_users cu
                    JOIN client_secrets cs ON cu.clients_id = cs.client_id
                    WHERE cu.id = :user_id AND cs.secret_key = 'database_url'
                """),
                {"user_id": test_client_data["client_user_id"]}
            )
            db_url = result.scalar_one()
            
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        # Connect to client database and insert test data
        engine = create_async_engine(db_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            # First, delete any existing test data
            await session.execute(
                text("DELETE FROM book_ingestions WHERE book_key = :book_key"),
                {"book_key": test_client_data["book_key"]}
            )
            
            # Insert sample pages
            for page in sample_pages:
                await session.execute(
                    text("""
                        INSERT INTO book_ingestions 
                        (book_key, page_number, page_text, file_name, language_code, version, created_at)
                        VALUES (:book_key, :page_number, :page_text, :file_name, :language_code, 'original', NOW())
                    """),
                    {
                        "book_key": test_client_data["book_key"],
                        "page_number": page["page_number"],
                        "page_text": page["page_text"],
                        "file_name": page["file_name"],
                        "language_code": page["language_code"]
                    }
                )
            
            await session.commit()
        
        await engine.dispose()
    
    async def get_translations(self, test_client_data):
        """Retrieve translated pages from database."""
        async with get_db_session() as session:
            # Get client database URL
            result = await session.execute(
                text("""
                    SELECT cs.secret_value 
                    FROM client_users cu
                    JOIN client_secrets cs ON cu.clients_id = cs.client_id
                    WHERE cu.id = :user_id AND cs.secret_key = 'database_url'
                """),
                {"user_id": test_client_data["client_user_id"]}
            )
            db_url = result.scalar_one()
            
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        # Connect to client database and get translations
        engine = create_async_engine(db_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        translations = []
        async with async_session() as session:
            result = await session.execute(
                text("""
                    SELECT page_number, page_text, language_code, version
                    FROM book_ingestions
                    WHERE book_key = :book_key AND version = :version
                    ORDER BY page_number
                """),
                {
                    "book_key": test_client_data["book_key"],
                    "version": "translation_en"
                }
            )
            
            for row in result.fetchall():
                translations.append({
                    "page_number": row.page_number,
                    "page_text": row.page_text,
                    "language_code": row.language_code,
                    "version": row.version
                })
        
        await engine.dispose()
        return translations
    
    def validate_translation_quality(self, original, translation):
        """Validate that translation is complete, not a summary."""
        # Check length ratio - translation should be similar length
        original_length = len(original["page_text"])
        translation_length = len(translation["page_text"])
        length_ratio = translation_length / original_length
        
        # Translation should be 70-130% of original length
        assert 0.7 <= length_ratio <= 1.3, f"Translation length ratio {length_ratio} suggests summarization"
        
        # Check for key content preservation
        # Count paragraphs (double newlines)
        original_paragraphs = original["page_text"].count("\n\n")
        translation_paragraphs = translation["page_text"].count("\n\n")
        
        # Should have similar paragraph structure
        assert abs(original_paragraphs - translation_paragraphs) <= 2, "Paragraph structure significantly different"
        
        # Check that it's not a summary by looking for typical summary phrases
        summary_indicators = [
            "in summary", "to summarize", "the main points", "overview of",
            "briefly describes", "key themes", "main ideas", "in conclusion"
        ]
        
        translation_lower = translation["page_text"].lower()
        for indicator in summary_indicators:
            assert indicator not in translation_lower, f"Found summary indicator: {indicator}"
        
        # For page 1, check specific content is preserved
        if original["page_number"] == 1:
            # Should contain the date
            assert "1767" in translation["page_text"], "Date not preserved in translation"
            # Should contain character names
            assert "Cosimo" in translation["page_text"], "Main character name missing"
            assert "snails" in translation["page_text"] or "escargot" in translation["page_text"], "Key plot element (snails) missing"
        
        return True
    
    @pytest.mark.asyncio
    async def test_5_page_translation_quality(self, test_client_data, sample_spanish_pages):
        """Test translation quality with 5-page sample."""
        # Setup test data
        await self.setup_test_data(test_client_data, sample_spanish_pages)
        
        # Run translation
        inputs = {
            "client_user_id": test_client_data["client_user_id"],
            "book_key": test_client_data["book_key"],
            "target_language": "en"
        }
        
        result = kickoff(inputs)
        
        # Check execution completed
        assert result["status"] == "completed", f"Translation failed: {result.get('error', 'Unknown error')}"
        
        # Get translations
        translations = await self.get_translations(test_client_data)
        
        # Verify we have all 5 pages
        assert len(translations) == 5, f"Expected 5 translations, got {len(translations)}"
        
        # Validate each translation
        for i, (original, translation) in enumerate(zip(sample_spanish_pages, translations)):
            print(f"\nValidating page {i+1}...")
            print(f"Original length: {len(original['page_text'])}")
            print(f"Translation length: {len(translation['page_text'])}")
            
            assert translation["page_number"] == original["page_number"]
            assert translation["language_code"] == "en"
            assert translation["version"] == "translation_en"
            
            # Validate translation quality
            self.validate_translation_quality(original, translation)
            
            print(f"Page {i+1} validation passed ✓")
        
        print("\nAll translations validated successfully!")
        print("Translations are complete and not summaries.")
    
    async def cleanup_test_data(self, test_client_data):
        """Clean up test data after tests."""
        async with get_db_session() as session:
            # Get client database URL
            result = await session.execute(
                text("""
                    SELECT cs.secret_value 
                    FROM client_users cu
                    JOIN client_secrets cs ON cu.clients_id = cs.client_id
                    WHERE cu.id = :user_id AND cs.secret_key = 'database_url'
                """),
                {"user_id": test_client_data["client_user_id"]}
            )
            db_url = result.scalar_one()
            
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        # Connect to client database and clean up
        engine = create_async_engine(db_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            await session.execute(
                text("DELETE FROM book_ingestions WHERE book_key = :book_key"),
                {"book_key": test_client_data["book_key"]}
            )
            await session.commit()
        
        await engine.dispose()