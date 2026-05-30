import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.utils import class_weight
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import tensorflow as tf
from tensorflow.keras import Input, Model
from tensorflow.keras.layers import Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras import regularizers

RANDOM_SEED = 42
TEST_SIZE = 0.20
VAL_FRACTION_OF_TEMP = 0.5
BATCH_SIZE = 256
MAX_EPOCHS = 200
INITIAL_LR = 3e-4
PATIENCE_ES = 20
PATIENCE_RLR = 7
# ------------------------------------------------------------

np.random.seed(RANDOM_SEED)
tf.random.set_seed(RANDOM_SEED)


data_path = Path(__file__).parent / "adult1.csv"
df = pd.read_csv(data_path)

first6 = df.columns[:6].tolist()
bool_cols = df.columns[6:6+102].tolist()
target_col = df.columns[-1]


X = df[first6 + bool_cols].astype('float32')
y = df[target_col].astype('int32')

X_train, X_temp, y_train, y_temp = train_test_split(
    X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_SEED
)
X_val, X_test, y_val, y_test = train_test_split(
    X_temp, y_temp, test_size=VAL_FRACTION_OF_TEMP, stratify=y_temp, random_state=RANDOM_SEED
)

print("Shapes -> train:", X_train.shape, "val:", X_val.shape, "test:", X_test.shape)

scaler = StandardScaler()
X_train_num = scaler.fit_transform(X_train[first6])
X_val_num = scaler.transform(X_val[first6])
X_test_num = scaler.transform(X_test[first6])

X_train_final = np.hstack([X_train_num, X_train[bool_cols].values.astype('float32')])
X_val_final   = np.hstack([X_val_num,   X_val[bool_cols].values.astype('float32')])
X_test_final  = np.hstack([X_test_num,  X_test[bool_cols].values.astype('float32')])

input_dim = X_train_final.shape[1]
print("Final input dim:", input_dim)

USE_CLASS_WEIGHTS = False  
if USE_CLASS_WEIGHTS:
    classes = np.unique(y_train)
    cw = class_weight.compute_class_weight(class_weight='balanced', classes=classes, y=y_train)
    class_weights = {int(c): float(w) for c, w in zip(classes, cw)}
else:
    class_weights = None
print("Class weights:", class_weights)

def make_model(input_dim, lr=INITIAL_LR):
    inp = Input(shape=(input_dim,))

    x = Dense(
        256,
        activation='relu',
        kernel_regularizer=regularizers.l2(1e-4),
    )(inp)
    x = BatchNormalization()(x)
    x = Dropout(0.30)(x)

    x = Dense(
        256,
        activation='relu',
        kernel_regularizer=regularizers.l2(1e-4),
    )(x)
    x = BatchNormalization()(x)
    x = Dropout(0.30)(x)

    x = Dense(
        128,
        activation='relu',
        kernel_regularizer=regularizers.l2(1e-4),
    )(x)
    x = BatchNormalization()(x)
    x = Dropout(0.20)(x)

    x = Dense(
        64,
        activation='relu',
        kernel_regularizer=regularizers.l2(1e-4),
    )(x)
    x = BatchNormalization()(x)
    x = Dropout(0.15)(x)

    out = Dense(1, activation='sigmoid')(x)

    model = Model(inputs=inp, outputs=out)
    model.compile(
        optimizer=Adam(learning_rate=lr),
        loss='binary_crossentropy',
        metrics=[
            tf.keras.metrics.BinaryAccuracy(name='accuracy', threshold=0.5),
            tf.keras.metrics.AUC(name='auc'),
        ],
    )
    return model

model = make_model(input_dim)
model.summary()

es = EarlyStopping(monitor='val_accuracy', mode='max', patience=PATIENCE_ES, restore_best_weights=True, verbose=1)
rlr = ReduceLROnPlateau(monitor='val_accuracy', mode='max', factor=0.5, patience=PATIENCE_RLR, min_lr=1e-6, verbose=1)

history = model.fit(
    X_train_final, y_train,
    validation_data=(X_val_final, y_val),
    epochs=MAX_EPOCHS,
    batch_size=BATCH_SIZE,
    class_weight=class_weights,
    callbacks=[es, rlr],
    verbose=2
)

print("\nEvaluating on test set:")
eval_res = model.evaluate(X_test_final, y_test, verbose=0)
print("Test loss, accuracy, auc:", eval_res)

y_pred_proba = model.predict(X_test_final, batch_size=1024).ravel()
y_pred = (y_pred_proba >= 0.5).astype(int)

print("\nClassification report (test):")
print(classification_report(y_test, y_pred, digits=4))
print("Confusion matrix:\n", confusion_matrix(y_test, y_pred))
print("ROC AUC (test):", roc_auc_score(y_test, y_pred_proba))

model.save("nn_accept_reject_model.h5")
import joblib
joblib.dump(scaler, "scaler_first6.joblib")
print("Saved model and scaler.")    