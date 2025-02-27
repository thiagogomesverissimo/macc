# Generated by Django 4.1.1 on 2022-09-28 00:52

from django.db import migrations
import pandas as pd


def load_catalog(apps, schema_editor):
    Author = apps.get_model('corpus', 'Author')
    Translator = apps.get_model('corpus', 'Translator')
    Work = apps.get_model('corpus', 'Work')
    Place = apps.get_model('corpus', 'Place')
    Publisher = apps.get_model('corpus', 'Publisher')
    Collection = apps.get_model('corpus', 'Collection')
    Translation = apps.get_model('corpus', 'Translation')

    df = pd.read_csv(
        'corpus/migrations/data/timeline_machado.csv', na_values=['null'])

    people = (df['translator']
              .dropna()
              .apply(lambda s: s.split(';'))
              .explode()
              .apply(str.strip)
              .drop_duplicates()
              .apply(lambda s: s.split(maxsplit=1)))

    authors = [Author(first_name=first, last_name=last)
               for first, last in people
               if " ".join([first, last]) in ['Machado de Assis']]
    Author.objects.bulk_create(authors)

    translators = [Translator(first_name=first, last_name=last)
                   for first, last in people
                   if " ".join([first, last]) not in ['Machado de Assis']]
    Translator.objects.bulk_create(translators)

    places = (df[['city', 'country']]
              .dropna()
              .sort_values(by=['country', 'city'])
              .drop_duplicates()
              .apply(lambda row: Place(city=row.city, country=row.country), axis=1)
              .values)
    Place.objects.bulk_create(list(places))

    publishers = []
    for _, row in (df[['publisher', 'city', 'country']]
                   .dropna(subset=['publisher'])
                   .drop_duplicates()
                   .iterrows()):
        if row.isna().any():
            publishers.append(Publisher(name=row.publisher))
        else:
            place = Place.objects.filter(
                city=row.city, country=row.country).get()
            publishers.append(Publisher(name=row.publisher, place=place))
    Publisher.objects.bulk_create(publishers)

    for _, row in (df
                   .loc[df['work_id']
                        .str
                        .contains('RO\d{3}MA').fillna(False), :]
                   .iterrows()):
        work_authors = [
            Author.objects.filter(first_name=first_name,
                                  last_name=last_name).get()
            for first_name, last_name in map(lambda s: s.strip().split(maxsplit=1),
                                             row.translator.split(';'))
        ]
        work = Work(year=row.publication_year,
                    title=row.title_portuguese,
                    code=row.work_id)
        work.save()
        work.authors.set(work_authors)

    for _, row in (df
                   .loc[df['work_id']
                        .str
                        .contains('RO\d{3}TR\d{2}').fillna(False), :]
                   .dropna(subset=['translator'])
                   .iterrows()):
        work_translators = [
            Translator.objects.filter(first_name=first_name,
                                      last_name=last_name).get()
            for first_name, last_name in [s.strip().split(maxsplit=1)
                                          for s in row.translator.split(';')]
        ]
        try:
            publisher = Publisher.objects.filter(
                name=row.publisher).get()
        except Publisher.DoesNotExist:
            publisher = None
        translation = Translation(year=row.publication_year,
                                  title=row.title_english,
                                  work=Work.objects.filter(
                                      title=row.title_portuguese).get(),
                                  publisher=publisher,
                                  code=row.work_id)
        translation.save()
        translation.authors.set(work_translators)

    df2 = pd.read_csv(
        'corpus/migrations/data/collections.csv', na_values=['null'])

    for _, row in df2.iterrows():
        try:
            publisher = Publisher.objects.filter(
                name=row.publisher,
                place__city=row.city,
                place__country=row.country
            ).get()
        except Publisher.DoesNotExist:
            publisher = None
        collection_translators = [
            Translator.objects.filter(first_name=first_name,
                                      last_name=last_name).get()
            for first_name, last_name in [s.strip().split(maxsplit=1)
                                          for s in row.translator.split(';')]
        ]
        collection = Collection(year=row.year,
                                title=row['name'],
                                publisher=publisher,
                                code=row.work_id)
        collection.save()
        collection.authors.set(collection_translators)

    df3 = pd.read_csv(
        'corpus/migrations/data/short_stories_translations.csv', header=[0, 1])

    df3.columns = (list(df3.columns.get_level_values(0)[:7])
                   + list(df3.columns.get_level_values(1)[7:]))

    df3['CONTO'] = df3['CONTO'].str.extract('(.*) \(\d*\)')

    machado = Author.objects.filter(
        first_name='Machado', last_name='de Assis').get()
    for _, row in df3.iterrows():
        work = Work(year=row['ANO'],
                    title=row['CONTO'],
                    code=row['CÓDIGO PT'])
        work.save()
        work.authors.set([machado])
        work.refresh_from_db()
        for code, work_id in row[row.index.str.contains('CL')].dropna().items():
            collection = Collection.objects.filter(code=code).get()
            translation = Translation(year=collection.year,
                                      title=collection.title,
                                      work=work,
                                      collection=collection,
                                      code=work_id)
            translation.save()


def rollback_catalog(apps, schema_editor):
    Author = apps.get_model('corpus', 'Author')
    Translator = apps.get_model('corpus', 'Translator')
    Work = apps.get_model('corpus', 'Work')
    Place = apps.get_model('corpus', 'Place')
    Publisher = apps.get_model('corpus', 'Publisher')
    Collection = apps.get_model('corpus', 'Collection')
    Translation = apps.get_model('corpus', 'Translation')

    Translation.objects.all().delete()
    Collection.objects.all().delete()
    Publisher.objects.all().delete()
    Place.objects.all().delete()
    Work.objects.all().delete()
    Translator.objects.all().delete()
    Author.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('corpus', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(load_catalog, rollback_catalog)
    ]
